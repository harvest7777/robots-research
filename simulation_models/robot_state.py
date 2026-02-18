"""
Robot runtime state (mutable).

This module defines `RobotState`, the per-run, mutable state for a robot.

Separation of concerns:
- `Robot` (in `robot.py`) is the immutable robot definition + execution model
  (capabilities, speed, battery drain rates, etc.).
- `RobotState` is the data that changes every simulation tick (position, battery).
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
    position: Position
    battery_level: float = 1.0
