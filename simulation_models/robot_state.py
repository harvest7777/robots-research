"""
Robot runtime state (mutable).

This module defines `RobotState`, the per-run, mutable state for a robot.

Separation of concerns:
- `Robot` (in `robot.py`) is the immutable robot definition + execution model
  (capabilities, speed, battery drain rates, etc.).
- `RobotState` is the data that changes every simulation tick (position, battery).

Coordinate conventions:
- `RobotState` stores position internally as floats (`x`, `y`) to support smooth motion.
- The `position` property exposes a discrete `Position(x: int, y: int)` for grid logic.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation_models.assignment import RobotId
from simulation_models.position import Position


@dataclass
class RobotState:
    """
    Mutable runtime state for a robot within a single simulation run.

    Notes:
    - This object contains no decision logic.
    - It is mutated by the Simulation (directly) and by `Robot` execution methods.
    """

    robot_id: RobotId
    x: float
    y: float
    battery_level: float = 1.0

    @staticmethod
    def from_position(robot_id: RobotId, position: Position, battery_level: float = 1.0) -> "RobotState":
        """Create RobotState from an integer grid `Position`."""
        return RobotState(robot_id=robot_id, x=float(position.x), y=float(position.y), battery_level=battery_level)

    @property
    def position(self) -> Position:
        """Current position as discrete grid coordinates."""
        return Position(int(self.x), int(self.y))

