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
from typing import NewType

from simulation.primitives.position import Position

RobotId = NewType("RobotId", int)
"""Opaque identifier for robots. Hashable and comparable."""


@dataclass(frozen=True)
class RobotState:
    """
    Immutable runtime state for a robot within a single simulation run.

    Notes:
    - This object contains no decision logic.
    - Replaced entirely each tick by the applicator; never mutated in place.
    """

    robot_id: RobotId
    position: Position
    battery_level: float = 1.0
    current_waypoint: Position | None = None
