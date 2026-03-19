"""
RescuePoint model.

A RescuePoint is a discoverable location in the environment. When a search
robot finds it, RescuePoint.task and RescuePoint.initial_task_state are
spawned into the active task set.

RescuePoint is metadata only — it is NOT placed in the environment grid.
It is immutable (frozen dataclass).
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.primitives.position import Position
from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
from simulation.domain.task import SpatialConstraint


@dataclass(frozen=True)
class RescuePoint:
    """
    A rescue point: a discoverable location that spawns a task when found.

    Attributes:
        id:                  TaskId identifying this rescue point (used to track discovery).
        name:                Human-readable label for display and logging.
        spatial_constraint:  Detection range — where and how far a robot must be to discover.
        task:                The task spawned when this rescue point is discovered.
        initial_task_state:  The initial state for the spawned task.
    """

    id: TaskId
    name: str
    spatial_constraint: SpatialConstraint
    task: BaseTask
    initial_task_state: BaseTaskState

    @property
    def position(self) -> Position:
        """Exact grid cell where this rescue point is located."""
        if not isinstance(self.spatial_constraint.target, Position):
            raise TypeError(f"RescuePoint {self.id} target is not a Position")
        return self.spatial_constraint.target
