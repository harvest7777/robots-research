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

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType, TYPE_CHECKING

from .capability import Capability
from .position import Position
from .time import Time
from .zone import ZoneId

if TYPE_CHECKING:
    from .assignment import RobotId
    from .task_state import TaskState


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
    required_work_time: Time 
    spatial_constraint: SpatialConstraint | None = None
    required_capabilities: frozenset[Capability] = frozenset()
    dependencies: frozenset[TaskId] = frozenset()
    deadline: Time | None = None

    def set_assignment(self, state: TaskState, robot_ids: set[RobotId]) -> None:
        """
        Replace the current assignment on `state` with `robot_ids`.

        This is a task-centric view of assignment that supports multi-robot tasks.
        The Simulation engine decides when to call this (based on Coordinator output).
        """
        # Import locally to avoid import cycles at module import time.
        from .task_state import TaskStatus

        state.assigned_robot_ids = set(robot_ids)

        if not state.assigned_robot_ids and state.status in (TaskStatus.UNASSIGNED, TaskStatus.ASSIGNED):
            state.status = TaskStatus.UNASSIGNED
            return

        if state.assigned_robot_ids and state.status == TaskStatus.UNASSIGNED:
            state.status = TaskStatus.ASSIGNED

    def apply_work(self, state: TaskState, dt: Time, t_now: Time) -> None:
        """
        Apply linear work for `dt` ticks to `state`.

        This method does NOT decide *why* work is happening (robot location, comms,
        etc.). The Simulation engine calls it only when task constraints are satisfied.

        When accumulated work reaches `required_work_time`, the task is marked done.
        """
        from .task_state import TaskStatus

        if state.status in (TaskStatus.DONE, TaskStatus.FAILED):
            return

        if state.started_at is None:
            state.started_at = t_now

        state.status = TaskStatus.IN_PROGRESS
        state.work_done = state.work_done.advance(dt)

        if state.work_done.tick >= self.required_work_time.tick:
            self.mark_done(state, t_now)

    def mark_done(self, state: TaskState, t_now: Time) -> None:
        """Mark the task complete on `state` and clear assignment."""
        from .task_state import TaskStatus

        state.status = TaskStatus.DONE
        state.completed_at = t_now
        state.assigned_robot_ids.clear()

    def mark_failed(self, state: TaskState, t_now: Time) -> None:
        """Mark the task failed on `state` and clear assignment."""
        from .task_state import TaskStatus

        state.status = TaskStatus.FAILED
        state.completed_at = t_now
        state.assigned_robot_ids.clear()
