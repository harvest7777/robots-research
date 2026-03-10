"""
Task runtime state (mutable) and state-transition functions.

`Task` is an immutable definition (intent/constraints). `TaskState` is the per-run,
mutable state owned by the Simulation engine:
- lifecycle status (unassigned -> assigned -> in_progress -> done/failed)
- which robots are currently assigned
- when the task started and completed (in simulation `Time` ticks)
- how much work has been applied so far (linear progress in ticks)

Separation of concerns:
- Coordinator produces `Assignment`s.
- Simulation applies `Assignment`s and mutates `TaskState` via the functions here.
- `Task` (definition) is pure data; it has no methods that mutate state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from simulation_models.robot_state import RobotId
from simulation_models.task import TaskId
from simulation_models.time import Time


class TaskStatus(Enum):
    """Lifecycle status of a task within a single simulation run."""

    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


@dataclass
class TaskState:
    """
    Mutable runtime state for a `Task`.

    This is intentionally minimal. It does not store task intent (duration,
    capabilities, etc.)—that lives on `Task`.
    """

    task_id: TaskId
    status: TaskStatus = TaskStatus.UNASSIGNED

    # Current assignment (task-centric view; supports multi-robot tasks).
    assigned_robot_ids: set[RobotId] = field(default_factory=set)

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

def set_assignment(state: TaskState, robot_ids: set[RobotId]) -> None:
    """Replace the current assignment on `state` with `robot_ids`."""
    state.assigned_robot_ids = set(robot_ids)

    if not state.assigned_robot_ids and state.status in (TaskStatus.UNASSIGNED, TaskStatus.ASSIGNED):
        state.status = TaskStatus.UNASSIGNED
        return

    if state.assigned_robot_ids and state.status == TaskStatus.UNASSIGNED:
        state.status = TaskStatus.ASSIGNED


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
    """Mark the task complete on `state` and clear assignment."""
    state.status = TaskStatus.DONE
    state.completed_at = t_now
    state.assigned_robot_ids.clear()


def mark_failed(state: TaskState, t_now: Time) -> None:
    """Mark the task failed on `state` and clear assignment."""
    state.status = TaskStatus.FAILED
    state.completed_at = t_now
    state.assigned_robot_ids.clear()
