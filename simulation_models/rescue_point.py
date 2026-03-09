"""
RescuePoint model.

A RescuePoint represents a location where a survivor or target of interest
may be found during a search-and-rescue scenario.

Design principles:
- RescuePoint is metadata only — it is NOT placed in the environment grid.
  Robots can pass through and arrive at the cell without obstruction.
- RescuePoint is immutable (frozen dataclass).
- rescue_task_id couples the point to a pre-defined RESCUE task so the
  simulation knows exactly which task to trigger when the point is found.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType

from simulation_models.position import Position
from simulation_models.task import TaskId

RescuePointId = NewType("RescuePointId", int)
"""Opaque identifier for rescue points. Hashable and comparable."""


@dataclass(frozen=True)
class RescuePoint:
    """
    Immutable description of a rescue point location.

    Attributes:
        id: Unique identifier for this rescue point.
        position: Grid cell where the rescue point is located.
        name: Human-readable label (for display and logging).
        rescue_task_id: The pre-defined RESCUE task to trigger when found.
    """

    id: RescuePointId
    position: Position
    name: str
    rescue_task_id: TaskId
