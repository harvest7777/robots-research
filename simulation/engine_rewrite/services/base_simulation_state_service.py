"""
BaseSimulationStateService

Holds the runtime state layer: robot positions/battery and task progress.
The runner reads from this service at the start of each tick to build an
immutable SimulationState snapshot, then writes the result back after the
pure engine step completes.

This separation lets external consumers (e.g. an LLM on a separate thread)
read a consistent state snapshot at any time without coupling to the runner.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from simulation.domain.base_task import BaseTaskState, TaskId
from simulation.domain.robot_state import RobotId, RobotState


class BaseSimulationStateService(ABC):

    @abstractmethod
    def get_snapshot(self) -> tuple[dict[RobotId, RobotState], dict[TaskId, BaseTaskState]]:
        """Return a (robot_states, task_states) snapshot of the current tick.

        The returned dicts are independent copies — callers may not mutate them.
        """

    @abstractmethod
    def _set_state(
        self,
        robot_states: dict[RobotId, RobotState],
        task_states: dict[TaskId, BaseTaskState],
    ) -> None:
        """Overwrite stored state with the results of the latest engine tick.

        Called by the runner after each step(). Replaces both dicts atomically.
        """