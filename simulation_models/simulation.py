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

from simulation_models.assignment import Assignment, RobotId
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.snapshot import SimulationSnapshot
from simulation_models.task import SpatialConstraint, Task, TaskId
from simulation_models.task_state import TaskState, TaskStatus
from simulation_models.time import Time
from simulation_models.zone import ZoneId

AssignmentAlgorithm = Callable[[list[Task], list[Robot]], list[Assignment]]
"""A function that assigns robots to tasks."""

PathfindingAlgorithm = Callable[
    [Environment, Position, Position, frozenset[Position]],
    Position | None,
]
"""(environment, start, goal, occupied_by_other_robots) -> next_step or None."""


@dataclass
class Simulation:
    """
    Central container for simulation state and data.

    Data fields are required at construction. The assignment_algorithm is optional
    at construction but required before calling step().

    Attributes:
        environment: The grid environment with zones and obstacles.
        robots: List of robot definitions (immutable).
        tasks: List of task definitions (immutable).
        robot_states: Mutable state for each robot, keyed by robot_id.
        task_states: Mutable state for each task, keyed by task_id.
        assignment_algorithm: Algorithm that assigns robots to tasks. Optional at
            construction, but required before stepping.
        current_assignments: Assignments from the most recent step() call.
        t_now: Current simulation time.
        dt: Time step size per step() call.
        history: Snapshot history keyed by simulation time.
    """

    environment: Environment
    robots: list[Robot]
    tasks: list[Task]
    robot_states: dict[RobotId, RobotState]
    task_states: dict[TaskId, TaskState]
    assignment_algorithm: AssignmentAlgorithm | None = None
    pathfinding_algorithm: PathfindingAlgorithm | None = None
    current_assignments: list[Assignment] = field(default_factory=list)
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

        # Record initial snapshot at t_now=0
        self.history[self.t_now] = self.snapshot()

    def _validate_ready(self) -> None:
        """Validate that simulation is ready to step.

        Raises:
            ValueError: If assignment_algorithm or pathfinding_algorithm is not set.
        """
        if self.assignment_algorithm is None:
            raise ValueError(
                "Simulation requires 'assignment_algorithm' before stepping"
            )
        if self.pathfinding_algorithm is None:
            raise ValueError(
                "Simulation requires 'pathfinding_algorithm' before stepping"
            )

    def step(self) -> None:
        """Execute one simulation tick.

        Two-phase approach to prevent move-order bias:

        Plan phase: compute next positions for all robots before moving any.
        Execute phase: move robots, apply work, update task states.

        Raises:
            ValueError: If simulation is not ready.
        """
        self._validate_ready()

        # Advance simulation time
        self.t_now = self.t_now.advance(self.dt)

        # Run assignment algorithm
        self.current_assignments = self.assignment_algorithm(self.tasks, self.robots)

        # Build lookup: robot_id -> (task, task_state) for assigned robots
        robot_by_id = {r.id: r for r in self.robots}
        task_by_id = {t.id: t for t in self.tasks}
        robot_assignment: dict[RobotId, TaskId] = {}
        for assignment in self.current_assignments:
            for rid in assignment.robot_ids:
                robot_assignment[rid] = assignment.task_id

        # Update task assignment states
        for task in self.tasks:
            ts = self.task_states[task.id]
            assigned_rids = {
                rid for rid, tid in robot_assignment.items() if tid == task.id
            }
            task.set_assignment(ts, assigned_rids)

        # --- Plan phase ---
        all_positions = {
            rid: state.position for rid, state in self.robot_states.items()
        }
        planned_moves: dict[RobotId, Position | None] = {}

        for rid, state in self.robot_states.items():
            if rid not in robot_assignment:
                planned_moves[rid] = None
                continue

            tid = robot_assignment[rid]
            task = task_by_id[tid]
            ts = self.task_states[tid]

            if ts.status in (TaskStatus.DONE, TaskStatus.FAILED):
                planned_moves[rid] = None
                continue

            goal = self._resolve_goal(task, state.position)
            if goal is None:
                # No spatial constraint — robot works in place
                planned_moves[rid] = None
                continue

            if state.position == goal:
                planned_moves[rid] = None
                continue

            occupied = frozenset(
                pos for other_rid, pos in all_positions.items() if other_rid != rid
            )
            next_step = self.pathfinding_algorithm(
                self.environment, state.position, goal, occupied
            )
            planned_moves[rid] = next_step

        # Detect planned collisions: two robots targeting the same cell
        target_counts: dict[Position, list[RobotId]] = {}
        for rid, next_pos in planned_moves.items():
            if next_pos is not None:
                target_counts.setdefault(next_pos, []).append(rid)
        for pos, rids in target_counts.items():
            if len(rids) > 1:
                # Only first robot proceeds, others stay put
                for rid in rids[1:]:
                    planned_moves[rid] = None

        # --- Execute phase ---
        for rid, state in self.robot_states.items():
            robot = robot_by_id[rid]
            next_pos = planned_moves.get(rid)

            if rid not in robot_assignment:
                robot.idle(state, self.dt)
                continue

            tid = robot_assignment[rid]
            task = task_by_id[tid]
            ts = self.task_states[tid]

            if ts.status in (TaskStatus.DONE, TaskStatus.FAILED):
                robot.idle(state, self.dt)
                continue

            goal = self._resolve_goal(task, state.position)

            if next_pos is not None and next_pos != state.position:
                # Robot has a move to make
                robot.move_towards(state, next_pos, self.dt)
            elif goal is None or state.position == goal:
                # At goal or no spatial constraint — do work
                robot.work(state, self.dt)
                task.apply_work(ts, self.dt, self.t_now)
            else:
                # Stuck (pathfinding returned None, or collision-blocked)
                robot.idle(state, self.dt)

        # Record snapshot at new time
        self.history[self.t_now] = self.snapshot()

    def _resolve_goal(self, task: Task, robot_pos: Position) -> Position | None:
        """Resolve a task's spatial constraint to a concrete Position.

        Returns:
            The target Position, or None if the task has no spatial constraint.
        """
        sc = task.spatial_constraint
        if sc is None:
            return None

        if isinstance(sc.target, Position):
            return sc.target

        # ZoneId — find nearest zone cell to the robot
        zone = self.environment.get_zone(sc.target)
        if zone is None:
            return None

        return min(
            zone.cells,
            key=lambda cell: abs(cell.x - robot_pos.x) + abs(cell.y - robot_pos.y),
        )

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

        return SimulationSnapshot(
            env=self.environment,
            robots=tuple(self.robots),
            robot_states=MappingProxyType(robot_states_copy),
            tasks=tuple(self.tasks),
            task_states=MappingProxyType(task_states_copy),
            t_now=self.t_now,
        )