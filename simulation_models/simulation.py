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
from simulation_models.task import Task, TaskId
from simulation_models.task_state import TaskState
from simulation_models.time import Time

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
            ValueError: If assignment_algorithm is not set.
        """
        if self.assignment_algorithm is None:
            raise ValueError(
                "Simulation requires 'assignment_algorithm' before stepping"
            )

    def step(self) -> None:
        """Execute one simulation tick.

        Advances simulation time by dt, runs the assignment algorithm, and
        records a snapshot in history.

        Raises:
            ValueError: If simulation is not ready (missing assignment_algorithm).
        """
        self._validate_ready()

        # Advance simulation time
        self.t_now = self.t_now.advance(self.dt)

        # Run assignment algorithm
        self.current_assignments = self.assignment_algorithm(self.tasks, self.robots)

        # Record snapshot at new time
        self.history[self.t_now] = self.snapshot()

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
