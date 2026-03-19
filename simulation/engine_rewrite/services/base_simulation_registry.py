"""
BaseSimulationRegistry

Holds robot and task definitions — the static, slowly-changing layer of the
simulation. Supersedes BaseTaskRegistry by combining task and robot lookups
into one interface so both are visible to the LLM and to the runner.

The registry has no opinion on runtime state (positions, battery, work done)
or on assignment (that's BaseAssignmentService). It is the source of truth
for *what* exists in the simulation, not *where* it is or *who* is doing it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from simulation.domain.base_task import BaseTask, TaskId
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId


class BaseSimulationRegistry(ABC):

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    @abstractmethod
    def add_task(self, task: BaseTask) -> None:
        """Add or overwrite a task definition."""

    @abstractmethod
    def get_task(self, task_id: TaskId) -> BaseTask | None:
        """Return the task with the given ID, or None."""

    @abstractmethod
    def all_tasks(self) -> list[BaseTask]:
        """Return every registered task."""

    # ------------------------------------------------------------------
    # Robots
    # ------------------------------------------------------------------

    @abstractmethod
    def add_robot(self, robot: Robot) -> None:
        """Add or overwrite a robot definition."""

    @abstractmethod
    def get_robot(self, robot_id: RobotId) -> Robot | None:
        """Return the robot with the given ID, or None."""

    @abstractmethod
    def all_robots(self) -> list[Robot]:
        """Return every registered robot."""
