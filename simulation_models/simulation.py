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
        # Current occupancy: positions held by all robots right now
        current_positions: dict[RobotId, Position] = {
            robot_id: state.position
            for robot_id, state in self.robot_states.items()
        }
        planned_moves: dict[RobotId, Position | None] = {}

        for robot_id, state in self.robot_states.items():
            if robot_id not in robot_to_task:
                planned_moves[robot_id] = None
                continue

            task_id = robot_to_task[robot_id]
            task = self._task_by_id[task_id]
            task_state = self.task_states[task_id]

            if task_state.status in (TaskStatus.DONE, TaskStatus.FAILED):
                planned_moves[robot_id] = None
                continue

            if task.type == TaskType.IDLE:
                planned_moves[robot_id] = None
                continue

            goal = self._resolve_task_target_position(task, state.position)
            if goal is None:
                # No spatial constraint — robot works in place
                planned_moves[robot_id] = None
                continue

            if state.position == goal:
                planned_moves[robot_id] = None
                continue

            next_step = self.pathfinding_algorithm(
                self.environment, state.position, goal
            )
            planned_moves[robot_id] = next_step

        # --- Collision resolution ---
        # No two robots may occupy the same cell. A robot's planned move is
        # cancelled if its target cell is already occupied by another robot
        # (current position) or claimed by another robot's planned move.
        #
        # We resolve greedily in robot_id order. Priority between equal-priority
        # robots is arbitrary but deterministic.
        claimed: dict[Position, RobotId] = {}

        # Robots that aren't moving hold their current cell
        for robot_id, next_pos in planned_moves.items():
            if next_pos is None:
                pos = current_positions[robot_id]
                claimed[pos] = robot_id

        # Process moving robots in stable order
        for robot_id in sorted(planned_moves):
            next_pos = planned_moves[robot_id]
            if next_pos is None:
                continue
            if next_pos in claimed:
                # Cell taken — robot stays put
                planned_moves[robot_id] = None
                claimed[current_positions[robot_id]] = robot_id
            else:
                claimed[next_pos] = robot_id

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
                else self._get_eligible_robot_ids_for_task(
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

    @staticmethod
    def _get_eligible_robot_ids_for_task(
        task: Task,
        task_states: dict[TaskId, TaskState],
        robots: dict[RobotId, Robot],
        robot_states: dict[RobotId, RobotState],
        environment: Environment,
        time: Time,
    ) -> list[RobotId]:
        """Return IDs of robots eligible to work on task this tick.

        Returns empty list if the task is in a terminal state, past its
        deadline, or has unfinished dependencies. Otherwise filters
        task_states[task.id].assigned_robot_ids down to robots that
        satisfy all per-robot constraints (capabilities, battery, spatial).
        """
        task_state = task_states[task.id]

        # Task-level guards: terminal status, deadline, unmet dependencies
        if task_state.status in (TaskStatus.DONE, TaskStatus.FAILED):
            return []
        if task.deadline is not None and time.tick > task.deadline.tick:
            return []
        if any(task_states[dep].status != TaskStatus.DONE for dep in task.dependencies):
            return []

        # Per-robot filtering
        eligible = []
        for robot_id in task_state.assigned_robot_ids:
            robot = robots[robot_id]
            state = robot_states[robot_id]

            if state.battery_level <= 0.0:
                continue
            if not task.required_capabilities.issubset(robot.capabilities):
                continue
            if task.spatial_constraint is not None:
                sc = task.spatial_constraint
                if isinstance(sc.target, Position):
                    dist = state.position.manhattan(sc.target)
                    tolerance = sc.max_distance if sc.max_distance > 0 else 0
                    if dist > tolerance:
                        continue
                else:
                    zone = environment.get_zone(sc.target)
                    if zone is None:
                        continue
                    if zone.contains(state.position):
                        pass  # in zone, eligible
                    elif sc.max_distance == 0:
                        continue
                    else:
                        nearest_dist = min(
                            state.position.manhattan(cell) for cell in zone.cells
                        )
                        if nearest_dist > sc.max_distance:
                            continue

            eligible.append(robot_id)

        return eligible

    def _resolve_task_target_position(self, task: Task, robot_pos: Position) -> Position | None:
        """Resolve a task's spatial constraint to a concrete Position.

        Returns:
            The target Position, or None if the task has no spatial constraint.
        """
        sc = task.spatial_constraint
        if sc is None:
            return None

        if isinstance(sc.target, Position):
            return sc.target

        # ZoneId — find nearest zone cell to the robot (Manhattan distance)
        zone = self.environment.get_zone(sc.target)
        if zone is None:
            return None

        return min(
            zone.cells,
            key=lambda cell: robot_pos.manhattan(cell),
        )

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
        )
