"""
InMemorySimulationStore

In-memory implementation of BaseSimulationStore. Delegates to
InMemorySimulationRegistry and InMemorySimulationStateService internally.
Suitable for tests, scenarios, and any context where persistence is not needed.
"""

from __future__ import annotations

from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState

from .base_simulation_store import BaseSimulationStore
from .in_memory_simulation_registry import InMemorySimulationRegistry
from .in_memory_simulation_state_service import InMemorySimulationStateService


class InMemorySimulationStore(BaseSimulationStore):

    def __init__(self) -> None:
        self._registry = InMemorySimulationRegistry()
        self._state = InMemorySimulationStateService()

    # ------------------------------------------------------------------
    # Setup API
    # ------------------------------------------------------------------

    def add_robot(self, robot: Robot, state: RobotState) -> None:
        self._registry.add_robot(robot)
        self._state.init_robot(robot.id, state)

    def add_task(self, task: BaseTask, state: BaseTaskState) -> None:
        self._registry.add_task(task)
        self._state.init_task(task.id, state)

    # ------------------------------------------------------------------
    # Runner read API
    # ------------------------------------------------------------------

    def all_robots(self) -> list[Robot]:
        return self._registry.all_robots()

    def all_tasks(self) -> list[BaseTask]:
        return self._registry.all_tasks()

    def get_snapshot(self) -> tuple[dict[RobotId, RobotState], dict[TaskId, BaseTaskState]]:
        return self._state.get_snapshot()

    # ------------------------------------------------------------------
    # Runner write API
    # ------------------------------------------------------------------

    def apply(
        self,
        robot_states: dict[RobotId, RobotState],
        task_states: dict[TaskId, BaseTaskState],
    ) -> None:
        self._state._set_state(robot_states, task_states)

