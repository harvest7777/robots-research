"""
BaseSimulationStore

Unified store that combines the registry (robot/task definitions) and the
runtime state service (positions, battery, task progress) into a single
interface.

The split between registry and state service was an implementation detail; it
leaked through to SimulationRunner, which was forced to proxy add_robot() and
add_task() calls to two separate services.  The store merges that responsibility
so callers always add a definition and its initial state together — you cannot
accidentally register a robot without state, or state without a definition.

Two-tier API
------------
Setup (called by scenarios / app setup code):
    store.add_robot(robot, state)
    store.add_task(task, state)

Runner runtime (called internally by SimulationRunner.step()):
    store.all_robots()
    store.all_tasks()
    store.get_snapshot()
    store.apply(robot_states, task_states)
    store.add_task(task, state)   # also used for engine-spawned tasks
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState


class BaseSimulationStore(ABC):

    # ------------------------------------------------------------------
    # Setup API
    # ------------------------------------------------------------------

    @abstractmethod
    def add_robot(self, robot: Robot, state: RobotState) -> None:
        """Register a robot definition and its initial runtime state."""

    @abstractmethod
    def add_task(self, task: BaseTask, state: BaseTaskState) -> None:
        """Register a task definition and its initial runtime state."""

    # ------------------------------------------------------------------
    # Runner read API
    # ------------------------------------------------------------------

    @abstractmethod
    def all_robots(self) -> list[Robot]:
        """Return every registered robot definition."""

    @abstractmethod
    def all_tasks(self) -> list[BaseTask]:
        """Return every registered task definition."""

    @abstractmethod
    def get_snapshot(self) -> tuple[dict[RobotId, RobotState], dict[TaskId, BaseTaskState]]:
        """Return a (robot_states, task_states) snapshot of the current tick.

        The returned dicts are independent copies — callers may not mutate them.
        """

    # ------------------------------------------------------------------
    # Runner write API
    # ------------------------------------------------------------------

    @abstractmethod
    def apply(
        self,
        robot_states: dict[RobotId, RobotState],
        task_states: dict[TaskId, BaseTaskState],
    ) -> None:
        """Overwrite stored state with the results of the latest engine tick."""

