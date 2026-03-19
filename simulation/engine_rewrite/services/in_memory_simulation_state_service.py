"""
InMemorySimulationStateService

In-memory implementation of BaseSimulationStateService.
"""

from __future__ import annotations

from simulation.domain.base_task import BaseTaskState, TaskId
from simulation.domain.robot_state import RobotId, RobotState

from .base_simulation_state_service import BaseSimulationStateService


class InMemorySimulationStateService(BaseSimulationStateService):

    def __init__(self) -> None:
        self._robot_states: dict[RobotId, RobotState] = {}
        self._task_states: dict[TaskId, BaseTaskState] = {}

    def get_snapshot(self) -> tuple[dict[RobotId, RobotState], dict[TaskId, BaseTaskState]]:
        return dict(self._robot_states), dict(self._task_states)

    def apply(
        self,
        robot_states: dict[RobotId, RobotState],
        task_states: dict[TaskId, BaseTaskState],
    ) -> None:
        # Replace references atomically — readers on other threads always see
        # a complete snapshot, never a half-written state.
        self._robot_states = dict(robot_states)
        self._task_states = dict(task_states)

    def init_robot(self, robot_id: RobotId, state: RobotState) -> None:
        self._robot_states[robot_id] = state

    def init_task(self, task_id: TaskId, state: BaseTaskState) -> None:
        self._task_states[task_id] = state
