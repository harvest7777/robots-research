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
- Rescue points become active tasks on discovery (not pre-seeded)
"""

from __future__ import annotations

from simulation.algorithms.movement_planner import PathfindingAlgorithm, resolve_collisions
from simulation.algorithms.search_goal import compute_search_goal
from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId, TaskStatus
from simulation.domain.rescue_point import RescuePoint
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.search_task import SearchTask, SearchTaskState
from simulation.domain.task import WorkTask, SpatialConstraint
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
    robot_to_task: dict[RobotId, TaskId] = {
        assignment.robot_id: assignment.task_id for assignment in assignments
    }

    # -------------------------------------------------------------------------
    # Pass 1: validate assignments, compute intended moves
    # -------------------------------------------------------------------------
    valid: list[Assignment] = []
    # Seed all robots as stayers so idle robots block movers in collision resolution.
    intended_moves: dict[RobotId, Position | None] = {
        robot_id: None for robot_id in state.robot_states
    }

    for assignment in assignments:
        # Skip if this robot was superseded by a later assignment in the list.
        if robot_to_task.get(assignment.robot_id) != assignment.task_id:
            continue

        task = state.tasks.get(assignment.task_id)
        task_state = state.task_states.get(assignment.task_id)
        robot = state.robots.get(assignment.robot_id)
        robot_state = state.robot_states.get(assignment.robot_id)

        if task is None or task_state is None or robot is None or robot_state is None:
            continue

        reason = _ignore_reason(task, task_state, robot, robot_state)
        if reason is not None:
            outcome.assignments_ignored.append((assignment, reason))
            continue

        goal = _goal_for(task, robot_state, task_state, state, pathfinding)

        if goal is not None:
            outcome.waypoints[assignment.robot_id] = goal

        if goal is None or robot_state.position == goal:
            intended_moves[assignment.robot_id] = None
        else:
            next_position = pathfinding(state.environment, robot_state.position, goal)
            if next_position is None:
                outcome.assignments_ignored.append((assignment, IgnoreReason.NO_PATH))
                continue
            intended_moves[assignment.robot_id] = next_position

        valid.append(assignment)

    # -------------------------------------------------------------------------
    # Pass 2: resolve movement collisions
    # -------------------------------------------------------------------------
    current_positions: dict[RobotId, Position] = {
        robot_id: robot_state.position
        for robot_id, robot_state in state.robot_states.items()
    }
    resolved = resolve_collisions(intended_moves, current_positions)

    # -------------------------------------------------------------------------
    # Pass 3: classify moves and work
    # -------------------------------------------------------------------------
    worked_by_task: dict[TaskId, list[RobotId]] = {}

    for assignment in valid:
        robot_state = state.robot_states[assignment.robot_id]
        task = state.tasks[assignment.task_id]

        next_position = resolved.get(assignment.robot_id)
        effective_position = next_position if next_position is not None else robot_state.position

        if next_position is not None:
            outcome.moved.append((assignment.robot_id, next_position))

        # Search robots move but do not accumulate work — completion is event-driven.
        if isinstance(task, SearchTask):
            continue

        assert isinstance(task, WorkTask)
        if _robot_can_work(task, effective_position, state):
            outcome.worked.append((assignment.robot_id, assignment.task_id))
            worked_by_task.setdefault(assignment.task_id, []).append(assignment.robot_id)

    # -------------------------------------------------------------------------
    # Pass 4: work-accumulation task completions
    # -------------------------------------------------------------------------
    for task_id, workers in worked_by_task.items():
        task = state.tasks[task_id]
        task_state = state.task_states[task_id]
        assert isinstance(task, WorkTask) and isinstance(task_state, TaskState)
        new_work_ticks = task_state.work_done.tick + len(workers)
        if new_work_ticks >= task.required_work_time.tick:
            outcome.tasks_completed.append(task_id)

    # -------------------------------------------------------------------------
    # Pass 5: search discoveries — rescue points become active tasks on discovery
    # -------------------------------------------------------------------------
    search_assignments = [
        assignment for assignment in valid
        if isinstance(state.tasks.get(assignment.task_id), SearchTask)
    ]
    seen_rescue_ids: set[TaskId] = set()

    for assignment in sorted(search_assignments, key=lambda assignment: assignment.robot_id):  # deterministic order
        task_id = assignment.task_id
        task_state = state.task_states[task_id]
        assert isinstance(task_state, SearchTaskState)

        next_position = resolved.get(assignment.robot_id)
        effective_position = (
            next_position if next_position is not None
            else state.robot_states[assignment.robot_id].position
        )

        for rescue_point in state.environment.rescue_points.values():
            if task_state.rescue_found.get(rescue_point.id):
                continue
            if rescue_point.id in seen_rescue_ids:
                continue
            if effective_position == rescue_point.position:
                outcome.rescue_points_found.append(rescue_point.id)
                seen_rescue_ids.add(rescue_point.id)
                # The rescue point IS the task — no transformation needed.
                outcome.tasks_spawned.append(rescue_point)
                break

    # -------------------------------------------------------------------------
    # Pass 6: search task completions
    # -------------------------------------------------------------------------
    for assignment in search_assignments:
        task_id = assignment.task_id
        if task_id in outcome.tasks_completed:
            continue
        task_state = state.task_states[task_id]
        assert isinstance(task_state, SearchTaskState)

        newly_found = {
            rp_id for rp_id in outcome.rescue_points_found
            if rp_id in task_state.rescue_found
        }
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
    task: BaseTask,
    task_state: BaseTaskState,
    robot: Robot,
    robot_state: RobotState,
) -> IgnoreReason | None:
    if task_state.status in (TaskStatus.DONE, TaskStatus.FAILED):
        return IgnoreReason.TASK_TERMINAL
    if robot_state.battery_level <= 0.0:
        return IgnoreReason.NO_BATTERY
    if not task.required_capabilities.issubset(robot.capabilities):
        return IgnoreReason.WRONG_CAPABILITY
    return None


def _goal_for(
    task: BaseTask,
    robot_state: RobotState,
    task_state: BaseTaskState,
    state: SimulationState,
    pathfinding: PathfindingAlgorithm,
) -> Position | None:
    if isinstance(task, SearchTask):
        assert isinstance(task_state, SearchTaskState)
        return compute_search_goal(
            robot_state,
            state.environment.rescue_points,
            task_state.rescue_found,
            pathfinding,
            state.environment,
        )
    assert isinstance(task, WorkTask)
    return _resolve_spatial_target(task.spatial_constraint, robot_state.position, state)


def _resolve_spatial_target(
    spatial_constraint: SpatialConstraint | None,
    robot_position: Position,
    state: SimulationState,
) -> Position | None:
    if spatial_constraint is None:
        return None
    if isinstance(spatial_constraint.target, Position):
        return spatial_constraint.target
    zone = state.environment.get_zone(spatial_constraint.target)
    if zone is None:
        return None
    return min(zone.cells, key=lambda cell: robot_position.manhattan(cell))


def _robot_can_work(task: WorkTask, position: Position, state: SimulationState) -> bool:
    spatial_constraint = task.spatial_constraint
    if spatial_constraint is None:
        return True
    if isinstance(spatial_constraint.target, Position):
        tolerance = spatial_constraint.max_distance if spatial_constraint.max_distance > 0 else 0
        return position.manhattan(spatial_constraint.target) <= tolerance
    zone = state.environment.get_zone(spatial_constraint.target)
    if zone is None:
        return False
    if zone.contains(position):
        return True
    if spatial_constraint.max_distance > 0:
        return min(position.manhattan(cell) for cell in zone.cells) <= spatial_constraint.max_distance
    return False
