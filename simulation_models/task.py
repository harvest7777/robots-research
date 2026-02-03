"""
Task Definition Module

A Task is an immutable, declarative description of what outcome is required,
under what conditions it may start, and what prerequisites and resources it requires.

Design principles:
- Task describes intent and constraints only
- Task is immutable (frozen dataclass, frozenset for collections)
- Task contains NO execution state (no progress, timestamps, assigned robots)
- Task is serializable and replayable (IDs, enums, value objects only)
"""

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import NewType

from .capability import Capability
from .position import Position
from .time import Time
from .zone import ZoneId


# -----------------------------------------------------------------------------
# Supporting Types
# -----------------------------------------------------------------------------

TaskId = NewType("TaskId", int)
"""Opaque identifier for tasks. Hashable and comparable."""


class TaskType(Enum):
    """The kind of task to be performed."""

    ROUTINE_INSPECTION = "routine_inspection"
    ANOMALY_INVESTIGATION = "anomaly_investigation"
    PREVENTIVE_MAINTENANCE = "preventive_maintenance"
    EMERGENCY_RESPONSE = "emergency_response"
    PICKUP = "pickup"


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
class Task:
    """
    Immutable description of a task's intent and constraints.

    A Task declares:
    - What outcome is required (type, spatial_constraint)
    - What prerequisites it requires (dependencies, required_capabilities)
    - Scheduling hints (estimated_duration, deadline, priority)

    A Task does NOT contain:
    - Execution state (progress, start_time, completion_time)
    - Assignment state (assigned robots)
    - Runtime results (actual_duration)

    This object is safe to share, serialize, and reuse.
    """

    id: TaskId
    type: TaskType
    priority: int
    estimated_duration: timedelta
    spatial_constraint: SpatialConstraint | None = None
    required_capabilities: frozenset[Capability] = frozenset()
    dependencies: frozenset[TaskId] = frozenset()
    deadline: Time | None = None
