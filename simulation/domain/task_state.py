"""
Task runtime state (mutable) and state-transition functions.

`Task` is an immutable definition (intent/constraints). `TaskState` is the per-run,
mutable state owned by the Simulation engine:
- lifecycle status (unassigned -> in_progress -> done/failed)
- when the task started and completed (in simulation `Time` ticks)
- how much work has been applied so far (linear progress in ticks)

Who is assigned to a task is the sole responsibility of the AssignmentService and
the Assignment objects it produces. TaskState intentionally does not mirror that
information — doing so would create a second source of truth that can drift.

Separation of concerns:
- Coordinator produces `Assignment`s (owns robot-task binding).
- Simulation reads active `Assignment`s each tick and passes them to algorithms.
- `TaskState` tracks only work progress and completion timestamps.
- `Task` (definition) is pure data; it has no methods that mutate state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from simulation.domain.task import TaskId
from simulation.primitives.time import Time


class TaskStatus(Enum):
    """Lifecycle status of a task within a single simulation run."""

    UNASSIGNED = "unassigned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


@dataclass
class TaskState:
    """
    Mutable runtime state for a `Task`.

    This is intentionally minimal. It does not store task intent (duration,
    capabilities, etc.)—that lives on `Task`. It does not store assignment
    information—that lives in Assignment objects owned by the AssignmentService.
    """

    task_id: TaskId
    status: TaskStatus = TaskStatus.UNASSIGNED

    # Progress bookkeeping (opaque simulation ticks).
    work_done: Time = Time(0)

    # Key timestamps (opaque simulation ticks).
    started_at: Time | None = None
    completed_at: Time | None = None


# ---------------------------------------------------------------------------
# State-transition functions
# ---------------------------------------------------------------------------
# These functions own all logic for mutating TaskState. Task (the definition
# object) is pure data and has no methods that touch TaskState.

def apply_work(state: TaskState, required_work_time: Time, dt: Time, t_now: Time) -> None:
    """Apply linear work for `dt` ticks to `state`.

    When accumulated work reaches `required_work_time`, the task is marked done.
    """
    if state.status in (TaskStatus.DONE, TaskStatus.FAILED):
        return

    if state.started_at is None:
        state.started_at = t_now

    state.status = TaskStatus.IN_PROGRESS
    state.work_done = state.work_done.advance(dt)

    if state.work_done.tick >= required_work_time.tick:
        mark_done(state, t_now)


def mark_done(state: TaskState, t_now: Time) -> None:
    """Mark the task complete on `state`."""
    state.status = TaskStatus.DONE
    state.completed_at = t_now


def mark_failed(state: TaskState, t_now: Time) -> None:
    """Mark the task failed on `state`."""
    state.status = TaskStatus.FAILED
    state.completed_at = t_now
