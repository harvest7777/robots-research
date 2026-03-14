"""
BaseSimulationStateService: abstract interface for reading and writing simulation state.

The simulation writes a full snapshot of live state each tick.
The MCP server reads this state to give the LLM context before writing assignments.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from simulation.domain.robot_state import RobotId
from simulation.domain.task import TaskId
from simulation.domain.task_state import TaskStatus
from simulation.primitives.time import Time


@dataclass
class RobotStateSnapshot:
    robot_id: RobotId
    x: float
    y: float
    battery_level: float
    current_waypoint: tuple[int, int] | None = None


@dataclass
class TaskStateSnapshot:
    task_id: TaskId
    status: TaskStatus | None
    work_done_ticks: int
    assigned_robot_ids: list[RobotId]


@dataclass
class SimulationState:
    """Full live state of the simulation at a given tick."""
    scenario_id: str
    current_tick: int
    max_tick: int
    robots: list[RobotStateSnapshot]
    tasks: list[TaskStateSnapshot]


class BaseSimulationStateService(ABC):
    @abstractmethod
    def write(self, state: SimulationState) -> None:
        """Overwrite the stored state with the current simulation snapshot."""

    @abstractmethod
    def read(self) -> SimulationState | None:
        """Return the last written state, or None if nothing has been written yet."""

    @abstractmethod
    def update_current_tick(self, tick: int) -> None:
        """Update only the current_tick field in the stored state."""
