"""
Task runtime state (mutable) and state-transition functions.

`Task` is an immutable definition (intent/constraints). `TaskState` is the per-run,
mutable state owned by the Simulation engine:
- terminal status (DONE or FAILED), set explicitly by the engine
- when the task started and completed (in simulation `Time` ticks)
- how much work has been applied so far (linear progress in ticks)

## Design: why status is not derivable from TaskState alone

`TaskStatus.DONE` and `TaskStatus.FAILED` are the only statuses tracked here.
Both are terminal and must be set explicitly by the engine — they cannot be
inferred from `work_done` or `started_at` alone:

- `DONE` can be triggered by `mark_done()` even when `work_done` is zero
  (e.g. the rescue handler marks all SEARCH tasks done when a rescue point is
  found, regardless of how much work they accumulated).
- `FAILED` is set only by external engine logic; no field in TaskState encodes
  the condition that caused failure.

Non-terminal state is read directly from `started_at`:
- `started_at is None`     → task has not been started
- `started_at is not None` → task is in progress (and not yet terminal)

## Separation of concerns

- The AssignmentService owns robot-task bindings. TaskState has no knowledge
  of which robots are assigned — that would be a second source of truth.
- The engine (consumer) is the only caller of `mark_done` and `mark_failed`.
  TaskState does not self-transition; it is mutated from the outside.
- `Task` (definition) is pure data; it has no methods that mutate TaskState.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from simulation.domain.task import TaskId
from simulation.primitives.time import Time


class TaskStatus(Enum):
    """Terminal lifecycle status of a task.

    Only DONE and FAILED are tracked here. Both are set explicitly by the
    engine (the consumer of TaskState) and are not derivable from TaskState
    fields alone — see module docstring for the rationale.

    Non-terminal state (not started / in progress) is derived from
    `TaskState.started_at` by callers that need it.
    """

    DONE = "done"
    FAILED = "failed"


@dataclass
class TaskState:
    """
    Mutable runtime state for a `Task`.

    `status` is None until the engine explicitly marks the task terminal.
    `started_at` is set on the first call to `apply_work`; callers use it to
    distinguish "not yet started" (None) from "in progress" (not None, status
    is still None).

    Does not store assignment information — that lives in Assignment objects
    owned by the AssignmentService.
    """

    task_id: TaskId
    status: TaskStatus | None = None

    # Progress bookkeeping (opaque simulation ticks).
    work_done: Time = Time(0)

    # Key timestamps (opaque simulation ticks).
    started_at: Time | None = None
    completed_at: Time | None = None


# ---------------------------------------------------------------------------
# State-transition functions
# ---------------------------------------------------------------------------
# These functions own all logic for mutating TaskState. The engine calls them;
# TaskState does not self-transition.

def apply_work(state: TaskState, required_work_time: Time, dt: Time, t_now: Time) -> None:
    """Apply linear work for `dt` ticks to `state`.

    No-op if the task is already in a terminal state. Sets `started_at` on
    first call. Calls `mark_done` automatically when accumulated work reaches
    `required_work_time`.
    """
    if state.status in (TaskStatus.DONE, TaskStatus.FAILED):
        return

    if state.started_at is None:
        state.started_at = t_now

    state.work_done = state.work_done.advance(dt)

    if state.work_done.tick >= required_work_time.tick:
        mark_done(state, t_now)


def mark_done(state: TaskState, t_now: Time) -> None:
    """Mark the task terminal-successful.

    Called by the engine — either when `apply_work` accumulates enough work,
    or directly (e.g. the rescue handler marks SEARCH tasks done on discovery
    regardless of work_done). Not derivable from TaskState fields alone.
    """
    state.status = TaskStatus.DONE
    state.completed_at = t_now


def mark_failed(state: TaskState, t_now: Time) -> None:
    """Mark the task terminal-failed.

    Called by the engine when an external condition makes the task
    uncompletable. Not derivable from TaskState fields alone.
    """
    state.status = TaskStatus.FAILED
    state.completed_at = t_now
