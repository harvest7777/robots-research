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
# Task Definitions
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkTask(BaseTask):
    """
    Immutable description of any task that completes by accumulating
    robot-ticks of work at a spatial location.

    This is the clean base for work-accumulation tasks. It intentionally has
    no `type` field — task type is identified by isinstance checks, not enums.

    Phase 6 note: once the old engine is deleted, `Task` will be removed and
    `WorkTask` renamed to `Task`.
    """

    required_work_time: Time = Time(0)
    spatial_constraint: SpatialConstraint | None = None
    deadline: Time | None = None
    min_robots_needed: int = 1


@dataclass(frozen=True)
class Task(WorkTask):
    """
    Immutable description of a work-accumulation task.

    Extends WorkTask with a `type` enum for the old engine. The `type` field
    is legacy — the new engine identifies task kind via isinstance checks.
    Scheduled for removal in Phase 6 when the old engine is deleted.
    """

    type: TaskType = TaskType.ROUTINE_INSPECTION
