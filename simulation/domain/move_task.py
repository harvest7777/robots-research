"""
MoveTask and MoveTaskState.

A MoveTask represents an object that robots must collectively carry from its
current position to a destination.  At least min_robots_required robots must
be co-located with the task's current position for the task to advance one
step toward the destination each tick.

Business rules (enforced by the Observer):
- Robots assigned to a MoveTask navigate to the task's current_position.
- When >= min_robots_required robots reach current_position, the task moves
  one Manhattan step toward destination.
- The task completes when current_position == destination.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.domain.base_task import BaseTask, BaseTaskState
from simulation.primitives.position import Position


@dataclass(frozen=True)
class MoveTask(BaseTask):
    """Immutable definition of a task that must be physically moved."""

    destination: Position = Position(0, 0)
    min_robots_required: int = 1


@dataclass(frozen=True)
class MoveTaskState(BaseTaskState):
    """Runtime state tracking where a MoveTask currently is."""

    current_position: Position = Position(0, 0)
