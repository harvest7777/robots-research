"""
InMemorySimulationStore

In-memory implementation of BaseSimulationStore. Holds robot/task definitions
and runtime state directly. Suitable for tests, scenarios, and any context
where persistence is not needed.
"""

from __future__ import annotations

from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState

from .base_simulation_store import BaseSimulationStore


class InMemorySimulationStore(BaseSimulationStore):

    def __init__(self) -> None:
        self._robots: dict[RobotId, Robot] = {}
        self._tasks: dict[TaskId, BaseTask] = {}
        self._snapshot: tuple[dict[RobotId, RobotState], dict[TaskId, BaseTaskState]] = ({}, {})

    # ------------------------------------------------------------------
    # Setup API
    # ------------------------------------------------------------------

    def add_robot(self, robot: Robot, state: RobotState) -> None:
        self._robots[robot.id] = robot
        robot_states, task_states = self._snapshot
        new_robot_states = dict(robot_states)
        new_robot_states[robot.id] = state
        self._snapshot = (new_robot_states, task_states)

    def add_task(self, task: BaseTask, state: BaseTaskState) -> None:
        self._tasks[task.id] = task
        robot_states, task_states = self._snapshot
        new_task_states = dict(task_states)
        new_task_states[task.id] = state
        self._snapshot = (robot_states, new_task_states)

    # ------------------------------------------------------------------
    # Runner read API
    # ------------------------------------------------------------------

    def all_robots(self) -> list[Robot]:
        return list(self._robots.values())

    def all_tasks(self) -> list[BaseTask]:
        return list(self._tasks.values())

    def get_snapshot(self) -> tuple[dict[RobotId, RobotState], dict[TaskId, BaseTaskState]]:
        robot_states, task_states = self._snapshot
        return dict(robot_states), dict(task_states)

    # ------------------------------------------------------------------
    # Runner write API
    # ------------------------------------------------------------------

    def apply(
        self,
        robot_states: dict[RobotId, RobotState],
        task_states: dict[TaskId, BaseTaskState],
    ) -> None:
        self._snapshot = (dict(robot_states), dict(task_states))
