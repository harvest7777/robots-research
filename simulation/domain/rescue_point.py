"""
RescuePoint model.

A RescuePoint is both a location of interest in the environment AND a
work-accumulation task. When a search robot discovers it, the rescue point
itself is added to the active task set — no separate task object is created.

RescuePoint inherits from WorkTask, so it carries all task fields directly:
  - id (TaskId)            — the task ID; also serves as the rescue point identifier
  - spatial_constraint     — position with max_distance=0 (exact location)
  - required_work_time     — ticks of work to complete the rescue
  - min_robots_needed      — minimum robots to assign

The `position` property is a convenience accessor for
spatial_constraint.target, since rescue points are always at an exact cell.

Design principles:
- RescuePoint is metadata only — it is NOT placed in the environment grid.
  Robots can pass through and arrive at the cell without obstruction.
- RescuePoint is immutable (frozen dataclass).
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.domain.base_task import TaskId
from simulation.domain.task import WorkTask, SpatialConstraint

# RescuePointId is now an alias for TaskId — rescue points and their tasks
# share the same ID space. Kept as an alias so existing code compiles unchanged.
RescuePointId = TaskId


@dataclass(frozen=True)
class RescuePoint(WorkTask):
    """
    A rescue point: a discoverable location that becomes an active rescue task
    when found by a search robot.

    Attributes:
        id:                  TaskId identifying this rescue point and its task.
        priority:            Scheduling priority (higher = more urgent).
        spatial_constraint:  Exact position where rescue work must happen.
        required_work_time:  Ticks of work required to complete the rescue.
        min_robots_needed:   Minimum robots required for this rescue.
        name:                Human-readable label for display and logging.
    """

    name: str = ""
