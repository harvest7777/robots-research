"""
Simulation State Container

The Simulation class holds all state and data needed to run a simulation:
- Environment (grid, zones, obstacles)
- Robots (immutable definitions)
- Tasks (immutable definitions)
- Robot states (mutable, keyed by robot_id)
- Task states (mutable, keyed by task_id)
- Assignment algorithm (configurable by researchers)
- Time tracking (t_now, dt) and snapshot history
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Optional

from simulation_models.assignment import Assignment, RobotId
from services.base_assignment_service import BaseAssignmentService
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.simulation_result import SimulationResult
from simulation_models.snapshot import SimulationSnapshot
from simulation_models.task import Task, TaskId, TaskType
from simulation_models.task_state import TaskState, TaskStatus
from simulation_models.time import Time
from simulation_models.movement_planner import plan_moves, resolve_collisions, resolve_task_target_position
from simulation_models.step_context import StepContext
from simulation_models.rescue_handler import compute_rescue_effect
from simulation_models.search_goal import compute_search_goal
from simulation_models.work_eligibility import get_eligible_robots

PathfindingAlgorithm = Callable[
    [Environment, Position, Position],
    Position | None,
]
"""(environment, start, goal) -> next_step or None."""


@dataclass
class Simulation:
    """
    Central container for simulation state and data.

    Attributes:
        environment: The grid environment with zones and obstacles.
        robots: List of robot definitions (immutable).
        tasks: List of task definitions (immutable).
        robot_states: Mutable state for each robot, keyed by robot_id.
        task_states: Mutable state for each task, keyed by task_id.
        assignments: Fixed robot-task assignments to execute. Set before run().
        pathfinding_algorithm: Algorithm for computing robot movement.
        t_now: Current simulation time.
        dt: Time step size per step() call.
        history: Snapshot history keyed by simulation time.
    """

    environment: Environment
    robots: list[Robot]
    tasks: list[Task]
    robot_states: dict[RobotId, RobotState]
    task_states: dict[TaskId, TaskState]
    assignment_service: BaseAssignmentService | None = None
    pathfinding_algorithm: PathfindingAlgorithm | None = None
    t_now: Time = field(default_factory=lambda: Time(0))
    dt: Time = field(default_factory=lambda: Time(1))
    history: dict[Time, SimulationSnapshot] = field(default_factory=dict)
    rescue_found: dict = field(default_factory=dict)  # dict[RescuePointId, bool]
    rescue_proximity_threshold: int = 10  # Manhattan distance at which a SEARCH robot locks onto a rescue point

    def __post_init__(self) -> None:
        if self.environment is None:
            raise ValueError("Simulation requires 'environment'")
        if self.robots is None:
            raise ValueError("Simulation requires 'robots'")
        if self.tasks is None:
            raise ValueError("Simulation requires 'tasks'")
        if self.robot_states is None:
            raise ValueError("Simulation requires 'robot_states'")
        if self.task_states is None:
            raise ValueError("Simulation requires 'task_states'")

        # Build lookups for immutable robot/task lists
        self._robot_by_id: dict[RobotId, Robot] = {r.id: r for r in self.robots}
        self._task_by_id: dict[TaskId, Task] = {t.id: t for t in self.tasks}

        # Initialize rescue_found tracking from environment rescue points
        for rp_id in self.environment.rescue_points:
            if rp_id not in self.rescue_found:
                self.rescue_found[rp_id] = False

        # Record initial snapshot at t_now=0
        self.history[self.t_now] = self.snapshot()

    def _validate_ready(self) -> None:
        """Validate that simulation is ready to step.

        Raises:
            ValueError: If pathfinding_algorithm is not set.
        """
        if self.pathfinding_algorithm is None:
            raise ValueError(
                "Simulation requires 'pathfinding_algorithm' before stepping"
            )

    def run(
        self,
        max_delta_time: int,
        on_tick: Optional[Callable[["SimulationSnapshot"], None]] = None,
    ) -> SimulationResult:
        """Run the simulation to completion or until the time budget is exhausted.

        Terminates when all tasks are in a terminal state (DONE or FAILED) or
        when elapsed ticks since run() was called reaches max_delta_time,
        whichever comes first.

        Args:
            max_delta_time: Maximum ticks this run may consume before being
                forced to end. Measured from t_now at the time run() is called,
                so the cap is independent of the simulation's starting time.
            on_tick: Optional callback invoked after each tick with the new
                snapshot. Use this to write live state to an external store.

        Returns:
            SimulationResult with outcome metrics and the full snapshot history.
        """
        self._validate_ready()

        t_start = self.t_now
        terminal = {TaskStatus.DONE, TaskStatus.FAILED}

        # IDLE tasks never complete — exclude them from the termination check
        non_idle_task_ids = {
            t.id for t in self.tasks if t.type != TaskType.IDLE
        }

        while (self.t_now.tick - t_start.tick) < max_delta_time:
            if all(self.task_states[tid].status in terminal for tid in non_idle_task_ids):
                break
            self._step()
            if on_tick is not None:
                on_tick(self.history[self.t_now])

        all_terminal = all(self.task_states[tid].status in terminal for tid in non_idle_task_ids)
        tasks_succeeded = sum(
            1 for tid in non_idle_task_ids if self.task_states[tid].status == TaskStatus.DONE
        )
        elapsed = self.t_now.tick - t_start.tick

        return SimulationResult(
            completed=all_terminal,
            tasks_succeeded=tasks_succeeded,
            tasks_total=len(non_idle_task_ids),
            makespan=elapsed if all_terminal else None,
            snapshots=list(self.history.values()),
        )

    def _step(self) -> None:
        """Execute one simulation tick.

        Three-phase approach to prevent move-order and work-order bias:

        Plan phase:      compute next positions for all robots before moving any.
        Execute/move:    apply planned moves; track which robots moved.
        Execute/work:    snapshot eligibility across all tasks, then apply work
                         task-centrically so mid-loop completions cannot affect
                         sibling tasks within the same tick.
        """

        # Advance simulation time
        self.t_now = self.t_now.advance(self.dt)

        assignments = self._get_active_assignments()
        #
        robot_to_task: dict[RobotId, TaskId] = {
            rid: a.task_id for a in assignments for rid in a.robot_ids
        }

        # Update task assignment states based on active assignments
        for task in self.tasks:
            task_state = self.task_states[task.id]
            assigned_robot_ids = {
                rid for a in assignments if a.task_id == task.id for rid in a.robot_ids
            }
            task.set_assignment(task_state, assigned_robot_ids)

        # --- Plan phase ---
        ctx = StepContext(
            robot_states=self.robot_states,
            task_states=self.task_states,
            robot_to_task=robot_to_task,
            task_by_id=self._task_by_id,
            environment=self.environment,
            t_now=self.t_now,
        )

        current_positions: dict[RobotId, Position] = {
            robot_id: state.position
            for robot_id, state in self.robot_states.items()
        }

        def _goal_resolver(robot_id: RobotId, state: RobotState) -> Position | None:
            task = self._task_by_id[robot_to_task[robot_id]]
            if task.type == TaskType.SEARCH:
                goal = compute_search_goal(
                    state, self.environment.rescue_points, self.rescue_found,
                    self.rescue_proximity_threshold, self.pathfinding_algorithm,
                    self.environment,
                )
                state.current_waypoint = goal
                return goal
            return self._resolve_task_target_position(task, state.position)

        planned_moves = plan_moves(ctx, self.pathfinding_algorithm, _goal_resolver)

        # --- Collision resolution ---
        planned_moves = resolve_collisions(planned_moves, current_positions)

        # --- Post-plan rescue detection ---
        # Check if any SEARCH robot has reached an unfound rescue point.
        # Iterate in sorted robot_id order so the lowest-id robot wins if
        # multiple robots land on the same point in the same tick.
        search_robot_ids = [
            rid for rid, tid in robot_to_task.items()
            if self._task_by_id[tid].type == TaskType.SEARCH
        ]
        for robot_id in sorted(search_robot_ids):
            state = self.robot_states[robot_id]
            for rp in self.environment.rescue_points.values():
                if self.rescue_found.get(rp.id):
                    continue
                if state.position == rp.position:
                    self._trigger_rescue_found(rp, robot_to_task)
                    break

        # --- Execute phase: movement ---
        moved_set: set[RobotId] = set()

        for robot_id, next_pos in planned_moves.items():
            if next_pos is None:
                continue
            state = self.robot_states[robot_id]
            robot = self._robot_by_id[robot_id]
            robot.step_to(state, next_pos)
            moved_set.add(robot_id)

        # --- Execute phase: work ---
        # Snapshot eligibility against post-movement state before applying any
        # work, so task completions mid-loop cannot affect sibling tasks'
        # eligibility within the same tick.
        eligible_by_task: dict[TaskId, list[RobotId]] = {
            task.id: (
                []
                if task.type == TaskType.IDLE
                else get_eligible_robots(
                    task,
                    self.task_states,
                    self._robot_by_id,
                    self.robot_states,
                    self.environment,
                    self.t_now,
                )
            )
            for task in self.tasks
        }

        # Apply work for each task using the snapshot, then update robot states.
        worked_set: set[RobotId] = set()
        for task in self.tasks:
            eligible = eligible_by_task[task.id]
            if not eligible:
                continue
            task_state = self.task_states[task.id]
            task.apply_work(task_state, Time(self.dt.tick * len(eligible)), self.t_now)
            for robot_id in eligible:
                if robot_id not in moved_set:
                    robot = self._robot_by_id[robot_id]
                    robot.work(self.robot_states[robot_id])
                    worked_set.add(robot_id)

        # Robots that neither moved nor worked this tick are idling.
        for robot_id, state in self.robot_states.items():
            if robot_id not in moved_set and robot_id not in worked_set:
                self._robot_by_id[robot_id].idle(state)

        # Record snapshot at new time
        self.history[self.t_now] = self.snapshot()

    def _trigger_rescue_found(
        self, rp: object, robot_to_task: dict[RobotId, TaskId]
    ) -> None:
        effect = compute_rescue_effect(rp, robot_to_task, self._task_by_id, self.tasks, self.t_now)

        self.rescue_found.update(effect.rescue_found_updates)

        if self.assignment_service is not None:
            self.assignment_service.add_assignments([effect.new_assignment])

        for task_id in effect.tasks_to_mark_done:
            self._task_by_id[task_id].mark_done(self.task_states[task_id], self.t_now)

        for robot_id in effect.waypoints_to_clear:
            self.robot_states[robot_id].current_waypoint = None

    def _resolve_task_target_position(self, task: Task, robot_pos: Position) -> Position | None:
        return resolve_task_target_position(task, robot_pos, self.environment)

    def _get_active_assignments(self) -> list[Assignment]:
        """Return the active assignments at t_now via the assignment service."""
        if self.assignment_service is None:
            return []
        return self.assignment_service.get_assignments_for_time(self.t_now)

    def snapshot(self) -> SimulationSnapshot:
        """
        Create a read-only snapshot of current simulation state.

        The snapshot contains copies of all mutable state, so modifications to
        the returned snapshot will not affect the live simulation.

        Returns:
            SimulationSnapshot with copied state data wrapped in immutable views.
        """
        # Copy robot states (shallow copy is sufficient; fields are primitives)
        robot_states_copy = {
            rid: dataclasses.replace(state)
            for rid, state in self.robot_states.items()
        }

        # Copy task states (must copy the mutable assigned_robot_ids set)
        task_states_copy = {
            tid: TaskState(
                task_id=state.task_id,
                status=state.status,
                assigned_robot_ids=set(state.assigned_robot_ids),
                work_done=state.work_done,
                started_at=state.started_at,
                completed_at=state.completed_at,
            )
            for tid, state in self.task_states.items()
        }

        active_assignments = (
            self.assignment_service.get_assignments_for_time(self.t_now)
            if self.assignment_service is not None
            else []
        )

        return SimulationSnapshot(
            env=self.environment,
            robots=tuple(self.robots),
            robot_states=MappingProxyType(robot_states_copy),
            tasks=tuple(self.tasks),
            task_states=MappingProxyType(task_states_copy),
            t_now=self.t_now,
            active_assignments=tuple(active_assignments),
            rescue_found=MappingProxyType(dict(self.rescue_found)),
        )
