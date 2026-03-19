"""
MoveTask and MoveTaskState.

A MoveTask represents an object that robots must collectively carry from its
current position to a destination. Robots form a rigid-body formation with
the task object and move it one step per tick toward the destination.

Business rules (enforced by the Observer):
- A robot is eligible for the formation if it is within min_distance
  (Manhattan) of the task's current_position and passes standard checks
  (battery, capabilities).
- When >= min_robots_required eligible robots are present, the formation
  moves one step toward destination as a rigid body.
- The task completes when current_position == destination.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.domain.base_task import BaseTask, BaseTaskState
from simulation.primitives.position import Position


@dataclass(frozen=True)
class MoveTaskState(BaseTaskState):
    """Runtime state tracking where a MoveTask currently is."""

    current_position: Position = Position(0, 0)


@dataclass(frozen=True)
class MoveTask(BaseTask):
    """Immutable definition of a task that must be physically carried."""

    destination: Position = Position(0, 0)
    min_robots_required: int = 1
    min_distance: int = 1

