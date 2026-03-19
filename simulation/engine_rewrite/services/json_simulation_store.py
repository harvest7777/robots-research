"""
JsonSimulationStore

File-backed implementation of BaseSimulationStore. Delegates to
JsonSimulationRegistry (definitions) and JsonSimulationStateService (runtime
state) internally. Suitable for scenarios where an external consumer — such
as an LLM on a separate thread — reads state from disk between ticks.
"""

from __future__ import annotations

from pathlib import Path

from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState

from .base_assignment_service import BaseAssignmentService
from .base_simulation_store import BaseSimulationStore
from .json_simulation_registry import JsonSimulationRegistry
from .json_simulation_state_service import JsonSimulationStateService


class JsonSimulationStore(BaseSimulationStore):
    """Persists robot/task definitions and runtime state to JSON files.

    Args:
        registry_path:      Destination file for robot/task definitions.
        state_path:         Destination file for runtime state (written each tick).
        assignment_service: Provides current assignments at state-write time.
        scenario_id:        Written into the state JSON for consumer context.
        max_tick:           Written into the state JSON for consumer context.
    """

    def __init__(
        self,
        registry_path: Path,
        state_path: Path,
        assignment_service: BaseAssignmentService,
        scenario_id: str = "",
        max_tick: int = 0,
    ) -> None:
        self._registry = JsonSimulationRegistry(registry_path)
        self._state = JsonSimulationStateService(
            path=state_path,
            registry=self._registry,
            assignment_service=assignment_service,
            scenario_id=scenario_id,
            max_tick=max_tick,
        )

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
        self._state.apply(robot_states, task_states)

