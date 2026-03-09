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
import random
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
from simulation_models.movement_planner import resolve_collisions, resolve_task_target_position
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

            if task.type == TaskType.SEARCH:
                goal = self._compute_search_goal(robot_id, state)
            else:
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
        """Mark a rescue point found and reassign all SEARCH robots to its RESCUE task.

        Effects:
        1. Sets rescue_found[rp.id] = True.
        2. Collects all robot IDs currently on any SEARCH task.
        3. Adds an assignment for the RESCUE task covering all search robots.
        4. Marks all SEARCH tasks DONE (so the simulation can terminate).
        5. Clears current_waypoint for all reassigned robots.
        """
        self.rescue_found[rp.id] = True

        all_search_robot_ids = [
            rid for rid, tid in robot_to_task.items()
            if self._task_by_id[tid].type == TaskType.SEARCH
        ]

        if self.assignment_service is not None:
            self.assignment_service.add_assignments([
                Assignment(
                    task_id=rp.rescue_task_id,
                    robot_ids=frozenset(all_search_robot_ids),
                    assign_at=self.t_now,
                )
            ])

        # Mark SEARCH tasks done so the simulation termination check passes
        for task in self.tasks:
            if task.type == TaskType.SEARCH:
                task_state = self.task_states[task.id]
                task.mark_done(task_state, self.t_now)

        for robot_id in all_search_robot_ids:
            self.robot_states[robot_id].current_waypoint = None

    def _compute_search_goal(self, robot_id: RobotId, state: RobotState) -> Position | None:
        """Compute the roaming goal for a SEARCH robot.

        Priority order:
        1. Proximity lock: if any unfound rescue point is within Manhattan ≤ 4,
           lock the robot onto that rescue point's position.
        2. Keep current waypoint: if one is set and still reachable via A*.
        3. Random walkable cell: pick a new random non-obstacle position.

        Returns:
            The goal Position, or None if the environment is fully blocked.
        """
        # Step 1: Proximity lock onto any nearby unfound rescue point
        for rp in self.environment.rescue_points.values():
            if self.rescue_found.get(rp.id):
                continue
            if state.position.manhattan(rp.position) <= self.rescue_proximity_threshold:
                state.current_waypoint = rp.position
                return rp.position

        # Step 2: Keep existing waypoint if reachable and not yet reached
        if state.current_waypoint is not None and state.current_waypoint != state.position:
            next_step = self.pathfinding_algorithm(
                self.environment, state.position, state.current_waypoint
            )
            if next_step is not None:
                return state.current_waypoint
            # Waypoint unreachable — fall through to pick a new one
            state.current_waypoint = None

        # Step 3: Pick a random walkable position
        env = self.environment
        for _ in range(1000):
            x = random.randint(0, env.width - 1)
            y = random.randint(0, env.height - 1)
            pos = Position(x, y)
            if pos not in env.obstacles and pos != state.position:
                state.current_waypoint = pos
                return pos

        return None

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
