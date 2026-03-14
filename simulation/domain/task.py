"""
Task Definition Module

A Task is an immutable, declarative description of a work-accumulation goal:
what outcome is required, where it must happen, what prerequisites it needs,
and how many robots are needed.

Task extends BaseTask with fields that only apply to work-accumulation tasks.
Search behaviour lives in SearchTask (see search_task.py).

Design principles:
- Task describes intent and constraints only
- Task is immutable (frozen dataclass, frozenset for collections)
- Task contains NO execution state (no progress, timestamps, assigned robots)
- Task is serializable and replayable (IDs, enums, value objects only)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from simulation.primitives.capability import Capability  # noqa: F401 (re-export via BaseTask)
from simulation.primitives.position import Position
from simulation.primitives.time import Time
from simulation.primitives.zone import ZoneId

from simulation.domain.base_task import BaseTask, TaskId, TaskStatus  # noqa: F401 (re-export)


# -----------------------------------------------------------------------------
# Supporting Types
# -----------------------------------------------------------------------------

class TaskType(Enum):
    """The kind of work-accumulation task to be performed."""

    ROUTINE_INSPECTION = "routine_inspection"
    ANOMALY_INVESTIGATION = "anomaly_investigation"
    PREVENTIVE_MAINTENANCE = "preventive_maintenance"
    EMERGENCY_RESPONSE = "emergency_response"
    PICKUP = "pickup"
    IDLE = "idle"
    RESCUE = "rescue"


@dataclass(frozen=True)
class SpatialConstraint:
    """
    Describes where a task must be satisfied.

    Does not imply execution steps or contain environment logic.
    """

    target: Position | ZoneId
    max_distance: int = 0  # 0 = exact, > 0 = within distance


# -----------------------------------------------------------------------------
# Task Definition
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Task(BaseTask):
    """
    Immutable description of a work-accumulation task.

    Extends BaseTask with fields specific to tasks that complete by
    accumulating robot-ticks of work:
    - type: what kind of work (RESCUE, PICKUP, INSPECTION, etc.)
    - required_work_time: ticks of work needed for completion
    - spatial_constraint: where the work must happen
    - deadline: latest tick at which work is accepted
    - min_robots_needed: minimum robots to assign when triggered by a rescue

    Does NOT contain execution state (progress, timestamps, assigned robots).
    """

    type: TaskType = TaskType.ROUTINE_INSPECTION
    required_work_time: Time = Time(0)
    spatial_constraint: SpatialConstraint | None = None
    deadline: Time | None = None
    min_robots_needed: int = 1
