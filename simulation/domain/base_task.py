"""
Base task and base task state definitions.

These are the shared foundations for all task types in the simulation.
Concrete types (Task, SearchTask) extend BaseTask with type-specific fields.
Concrete states (TaskState, SearchTaskState) extend BaseTaskState likewise.

TaskId and TaskStatus live here to avoid circular imports — both Task and
TaskState depend on them, and both extend types defined in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType

from simulation.primitives.capability import Capability
from simulation.primitives.time import Time


# -----------------------------------------------------------------------------
# Shared primitives
# -----------------------------------------------------------------------------

TaskId = NewType("TaskId", int)
"""Opaque identifier for tasks. Hashable and comparable."""


class TaskStatus(Enum):
    """Terminal lifecycle status of a task.

    Only DONE and FAILED are tracked. Both are set explicitly by the engine
    and are not derivable from state fields alone.

    Non-terminal state (not started / in progress) is derived from
    type-specific fields (e.g. TaskState.started_at) by callers that need it.
    """

    DONE = "done"
    FAILED = "failed"


# -----------------------------------------------------------------------------
# Base definitions
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class BaseTask:
    """
    Shared immutable fields for all task types.

    Every task has an identity, a priority, capability requirements, and
    dependency edges. Type-specific fields (work time, spatial constraints,
    proximity threshold, etc.) live on concrete subclasses.
    """

    id: TaskId
    priority: int
    required_capabilities: frozenset[Capability] = frozenset()
    dependencies: frozenset[TaskId] = frozenset()


@dataclass(frozen=True)
class BaseTaskState:
    """
    Immutable runtime state for all task types.

    Tracks terminal status and completion timestamp. Type-specific progress
    fields (work_done, rescue_found, etc.) live on concrete subclasses.

    The engine is the only caller of mark_done / mark_failed. State does
    not self-transition.
    """

    task_id: TaskId
    status: TaskStatus | None = None
    completed_at: Time | None = None


# -----------------------------------------------------------------------------
# State-transition functions (shared across all task types)
# -----------------------------------------------------------------------------

def mark_done(state: BaseTaskState, t_now: Time) -> None:
    """Mark the task terminal-successful."""
    object.__setattr__(state, "status", TaskStatus.DONE)
    object.__setattr__(state, "completed_at", t_now)


def mark_failed(state: BaseTaskState, t_now: Time) -> None:
    """Mark the task terminal-failed."""
    object.__setattr__(state, "status", TaskStatus.FAILED)
    object.__setattr__(state, "completed_at", t_now)
