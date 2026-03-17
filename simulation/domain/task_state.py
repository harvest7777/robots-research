"""
Task runtime state (mutable) and work-accumulation transition function.

TaskState is the per-run mutable state for work-accumulation tasks (Task).
It extends BaseTaskState with work progress and timing bookkeeping.

mark_done and mark_failed live in base_task and operate on BaseTaskState,
so they work for all task types. They are re-exported here for callers
that import from this module.

apply_work is specific to work-accumulation tasks and lives here.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.domain.base_task import (  # noqa: F401 (re-export)
    BaseTaskState,
    TaskId,
    TaskStatus,
    mark_done,
    mark_failed,
)
from simulation.primitives.time import Time


@dataclass(frozen=True)
class TaskState(BaseTaskState):
    """
    Immutable runtime state for a work-accumulation Task.

    Extends BaseTaskState (task_id, status, completed_at) with:
    - work_done: accumulated robot-ticks of work
    - started_at: tick when first work was applied (None = not yet started)

    Does not store assignment information — that lives in Assignment objects
    owned by the AssignmentService.
    """

    work_done: Time = Time(0)
    started_at: Time | None = None


# ---------------------------------------------------------------------------
# Work-accumulation transition
# ---------------------------------------------------------------------------

def apply_work(state: TaskState, required_work_time: Time, dt: Time, t_now: Time) -> None:
    """Apply linear work for `dt` ticks to `state`.

    No-op if the task is already in a terminal state. Sets `started_at` on
    first call. Calls `mark_done` automatically when accumulated work reaches
    `required_work_time`.
    """
    if state.status in (TaskStatus.DONE, TaskStatus.FAILED):
        return

    if state.started_at is None:
        object.__setattr__(state, "started_at", t_now)

    object.__setattr__(state, "work_done", state.work_done.advance(dt))

    if state.work_done.tick >= required_work_time.tick:
        mark_done(state, t_now)
