"""
InMemorySimulationRegistry

In-memory implementation of BaseSimulationRegistry. Suitable for tests,
scenarios, and any context where persistence is not needed.
"""

from __future__ import annotations

from simulation.domain.base_task import BaseTask, TaskId
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId

from .base_simulation_registry import BaseSimulationRegistry


class InMemorySimulationRegistry(BaseSimulationRegistry):

    def __init__(
        self,
        tasks: list[BaseTask] | None = None,
        robots: list[Robot] | None = None,
    ) -> None:
        self._tasks: dict[TaskId, BaseTask] = {}
        self._robots: dict[RobotId, Robot] = {}
        for task in (tasks or []):
            self._tasks[task.id] = task
        for robot in (robots or []):
            self._robots[robot.id] = robot

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def add_task(self, task: BaseTask) -> None:
        self._tasks[task.id] = task

    def get_task(self, task_id: TaskId) -> BaseTask | None:
        return self._tasks.get(task_id)

    def all_tasks(self) -> list[BaseTask]:
        return list(self._tasks.values())

    # ------------------------------------------------------------------
    # Robots
    # ------------------------------------------------------------------

    def add_robot(self, robot: Robot) -> None:
        self._robots[robot.id] = robot

    def get_robot(self, robot_id: RobotId) -> Robot | None:
        return self._robots.get(robot_id)

    def all_robots(self) -> list[Robot]:
        return list(self._robots.values())
