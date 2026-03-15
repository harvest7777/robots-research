"""
Observer — classify_step (new design)

The single place all business rules live.

classify_step is a pure function: given current state and current assignments,
it returns a StepOutcome describing exactly what happens this tick.
It never mutates state and has no side effects.

Business rules enforced here:
- Terminal tasks produce no work (TASK_TERMINAL)
- Dead robots produce no work (NO_BATTERY)
- Capability mismatches produce no work (WRONG_CAPABILITY)
- Unreachable tasks produce no movement (NO_PATH)
- Robots move toward task targets via pathfinding
- Collision resolution: no two robots end on the same cell
- Work accumulates when a robot satisfies spatial constraints
- Work-accumulation tasks complete when required_work_time is reached
- Search robots roam and lock onto nearby rescue points
- Rescue points are discovered when a robot reaches the rescue point's position
- Search tasks complete when all rescue points in the environment are found
- Rescue tasks are spawned dynamically on discovery (not pre-seeded)
"""

from __future__ import annotations

from simulation.algorithms.movement_planner import PathfindingAlgorithm, resolve_collisions
from simulation.algorithms.search_goal import compute_search_goal
from simulation.domain.base_task import TaskId, TaskStatus
from simulation.domain.rescue_point import RescuePointId
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.search_task import SearchTask, SearchTaskState
from simulation.domain.task import Task, TaskType, SpatialConstraint
from simulation.domain.task_state import TaskState
from simulation.primitives.position import Position

from .assignment import Assignment
from .simulation_state import SimulationState
from .step_outcome import IgnoreReason, StepOutcome


def classify_step(
    state: SimulationState,
    assignments: list[Assignment],
    pathfinding: PathfindingAlgorithm,
) -> StepOutcome:
    """Classify one simulation tick into a StepOutcome.

    All business rules live here. Pure function — no mutations, no side effects.
    """
    outcome = StepOutcome()

    # Last assignment wins if a robot appears multiple times.
    robot_to_task: dict[RobotId, TaskId] = {a.robot_id: a.task_id for a in assignments}

    # -------------------------------------------------------------------------
    # Pass 1: validate assignments, compute intended moves
    # -------------------------------------------------------------------------
    valid: list[Assignment] = []
    intended_moves: dict[RobotId, Position | None] = {}

    for a in assignments:
        # Skip if this robot was superseded by a later assignment in the list.
        if robot_to_task.get(a.robot_id) != a.task_id:
            continue

        task = state.tasks.get(a.task_id)
        task_state = state.task_states.get(a.task_id)
        robot = state.robots.get(a.robot_id)
        robot_state = state.robot_states.get(a.robot_id)

        if None in (task, task_state, robot, robot_state):
            continue

        reason = _ignore_reason(task, task_state, robot, robot_state)
        if reason is not None:
            outcome.assignments_ignored.append((a, reason))
            continue

        goal = _goal_for(task, robot_state, task_state, state, pathfinding)

        if goal is None or robot_state.position == goal:
            intended_moves[a.robot_id] = None
        else:
            next_step = pathfinding(state.environment, robot_state.position, goal)
            if next_step is None:
                outcome.assignments_ignored.append((a, IgnoreReason.NO_PATH))
                continue
            intended_moves[a.robot_id] = next_step

        valid.append(a)

    # -------------------------------------------------------------------------
    # Pass 2: resolve movement collisions
    # -------------------------------------------------------------------------
    current_positions: dict[RobotId, Position] = {
        rid: s.position for rid, s in state.robot_states.items()
    }
    resolved = resolve_collisions(intended_moves, current_positions)

    # -------------------------------------------------------------------------
    # Pass 3: classify moves and work
    # -------------------------------------------------------------------------
    worked_by_task: dict[TaskId, list[RobotId]] = {}

    for a in valid:
        robot_state = state.robot_states[a.robot_id]
        task = state.tasks[a.task_id]

        next_pos = resolved.get(a.robot_id)
        effective_pos = next_pos if next_pos is not None else robot_state.position

        if next_pos is not None:
            outcome.moved.append((a.robot_id, next_pos))

        # Search robots move but do not accumulate work — completion is event-driven.
        if isinstance(task, SearchTask):
            continue

        assert isinstance(task, Task)
        if _robot_can_work(task, effective_pos, state):
            outcome.worked.append((a.robot_id, a.task_id))
            worked_by_task.setdefault(a.task_id, []).append(a.robot_id)

    # -------------------------------------------------------------------------
    # Pass 4: work-accumulation task completions
    # -------------------------------------------------------------------------
    for task_id, workers in worked_by_task.items():
        task = state.tasks[task_id]
        task_state = state.task_states[task_id]
        assert isinstance(task, Task) and isinstance(task_state, TaskState)
        new_work_ticks = task_state.work_done.tick + len(workers)
        if new_work_ticks >= task.required_work_time.tick:
            outcome.tasks_completed.append(task_id)

    # -------------------------------------------------------------------------
    # Pass 5: search discoveries and rescue task spawning
    # -------------------------------------------------------------------------
    search_valid = [a for a in valid if isinstance(state.tasks.get(a.task_id), SearchTask)]
    seen_rescue_ids: set[RescuePointId] = set()

    for a in sorted(search_valid, key=lambda x: x.robot_id):  # deterministic order
        task_id = a.task_id
        task_state = state.task_states[task_id]
        assert isinstance(task_state, SearchTaskState)

        next_pos = resolved.get(a.robot_id)
        effective_pos = next_pos if next_pos is not None else state.robot_states[a.robot_id].position

        for rp in state.environment.rescue_points.values():
            if task_state.rescue_found.get(rp.id):
                continue
            if rp.id in seen_rescue_ids:
                continue
            if effective_pos == rp.position:
                outcome.rescue_points_found.append((task_id, rp.id))
                seen_rescue_ids.add(rp.id)
                outcome.tasks_spawned.append(_make_rescue_task(rp, state))
                break

    # -------------------------------------------------------------------------
    # Pass 6: search task completions
    # -------------------------------------------------------------------------
    for a in search_valid:
        task_id = a.task_id
        if task_id in outcome.tasks_completed:
            continue
        task_state = state.task_states[task_id]
        assert isinstance(task_state, SearchTaskState)

        newly_found = {rp_id for tid, rp_id in outcome.rescue_points_found if tid == task_id}
        all_found = all(
            task_state.rescue_found.get(rp_id, False) or rp_id in newly_found
            for rp_id in state.environment.rescue_points
        )
        if all_found:
            outcome.tasks_completed.append(task_id)

    return outcome


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _ignore_reason(
    task: object,
    task_state: object,
    robot: Robot,
    robot_state: RobotState,
) -> IgnoreReason | None:
    from simulation.domain.base_task import BaseTaskState, TaskStatus
    assert isinstance(task_state, BaseTaskState)
    if task_state.status in (TaskStatus.DONE, TaskStatus.FAILED):
        return IgnoreReason.TASK_TERMINAL
    if robot_state.battery_level <= 0.0:
        return IgnoreReason.NO_BATTERY
    from simulation.domain.base_task import BaseTask
    assert isinstance(task, BaseTask)
    if not task.required_capabilities.issubset(robot.capabilities):
        return IgnoreReason.WRONG_CAPABILITY
    return None


def _goal_for(
    task: object,
    robot_state: RobotState,
    task_state: object,
    state: SimulationState,
    pathfinding: PathfindingAlgorithm,
) -> Position | None:
    if isinstance(task, SearchTask):
        assert isinstance(task_state, SearchTaskState)
        goal = compute_search_goal(
            robot_state,
            state.environment.rescue_points,
            task_state.rescue_found,
            task.proximity_threshold,
            pathfinding,
            state.environment,
        )
        robot_state.current_waypoint = goal
        return goal
    assert isinstance(task, Task)
    return _resolve_spatial_target(task.spatial_constraint, robot_state.position, state)


def _resolve_spatial_target(
    sc: SpatialConstraint | None,
    robot_pos: Position,
    state: SimulationState,
) -> Position | None:
    if sc is None:
        return None
    if isinstance(sc.target, Position):
        return sc.target
    zone = state.environment.get_zone(sc.target)
    if zone is None:
        return None
    return min(zone.cells, key=lambda cell: robot_pos.manhattan(cell))


def _robot_can_work(task: Task, position: Position, state: SimulationState) -> bool:
    sc = task.spatial_constraint
    if sc is None:
        return True
    if isinstance(sc.target, Position):
        tolerance = sc.max_distance if sc.max_distance > 0 else 0
        return position.manhattan(sc.target) <= tolerance
    zone = state.environment.get_zone(sc.target)
    if zone is None:
        return False
    if zone.contains(position):
        return True
    if sc.max_distance > 0:
        return min(position.manhattan(cell) for cell in zone.cells) <= sc.max_distance
    return False


def _make_rescue_task(rp: object, state: SimulationState) -> Task:
    from simulation.domain.rescue_point import RescuePoint
    from simulation.domain.base_task import TaskId
    from simulation.primitives.time import Time
    assert isinstance(rp, RescuePoint)
    new_id = TaskId(max(state.tasks.keys(), default=0) + 1)
    return Task(
        id=new_id,
        type=TaskType.RESCUE,
        priority=10,
        required_work_time=Time(rp.required_work_time),
        spatial_constraint=SpatialConstraint(target=rp.position, max_distance=0),
        min_robots_needed=rp.min_robots_needed,
    )
