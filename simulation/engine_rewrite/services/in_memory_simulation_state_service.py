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
        self._snapshot: tuple[dict[RobotId, RobotState], dict[TaskId, BaseTaskState]] = ({}, {})

    def get_snapshot(self) -> tuple[dict[RobotId, RobotState], dict[TaskId, BaseTaskState]]:
        robot_states, task_states = self._snapshot
        return dict(robot_states), dict(task_states)

    def _set_state(
        self,
        robot_states: dict[RobotId, RobotState],
        task_states: dict[TaskId, BaseTaskState],
    ) -> None:
        # Single reference assignment — readers see either the old or the new
        # snapshot, never a half-replaced state.
        self._snapshot = (dict(robot_states), dict(task_states))

    def init_robot(self, robot_id: RobotId, state: RobotState) -> None:
        robot_states, task_states = self._snapshot
        new_robot_states = dict(robot_states)
        new_robot_states[robot_id] = state
        self._snapshot = (new_robot_states, task_states)

    def init_task(self, task_id: TaskId, state: BaseTaskState) -> None:
        robot_states, task_states = self._snapshot
        new_task_states = dict(task_states)
        new_task_states[task_id] = state
        self._snapshot = (robot_states, new_task_states)
