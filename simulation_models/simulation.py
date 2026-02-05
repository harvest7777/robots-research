"""
Simulation State Container

The Simulation class holds all state and data needed to run a simulation:
- Environment (grid, zones, obstacles)
- Robots (immutable definitions)
- Tasks (immutable definitions)
- Robot states (mutable, keyed by robot_id)
- Task states (mutable, keyed by task_id)
- Assignment algorithm (configurable by researchers)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from simulation_models.assignment import Assignment, RobotId
from simulation_models.environment import Environment
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.task import Task, TaskId
from simulation_models.task_state import TaskState

AssignmentAlgorithm = Callable[[list[Task], list[Robot]], list[Assignment]]
"""A function that assigns robots to tasks."""


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
    """

    environment: Environment
    robots: list[Robot]
    tasks: list[Task]
    robot_states: dict[RobotId, RobotState]
    task_states: dict[TaskId, TaskState]
    assignment_algorithm: AssignmentAlgorithm | None = None

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

        Runs the assignment algorithm and applies assignments to task states.

        Raises:
            ValueError: If simulation is not ready (missing assignment_algorithm).
        """
        self._validate_ready()

        # Run assignment algorithm
        assignments = self.assignment_algorithm(self.tasks, self.robots)

        # Apply assignments to task states
        for assignment in assignments:
            task = next(t for t in self.tasks if t.id == assignment.task_id)
            task_state = self.task_states[assignment.task_id]
            task.set_assignment(task_state, set(assignment.robot_ids))