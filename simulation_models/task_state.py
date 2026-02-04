"""
Task runtime state (mutable).

`Task` is an immutable definition (intent/constraints). `TaskState` is the per-run,
mutable state owned by the Simulation engine:
- lifecycle status (unassigned -> assigned -> in_progress -> done/failed)
- which robots are currently assigned
- when the task started and completed (in simulation `Time` ticks)
- how much work has been applied so far (linear progress in ticks)

Separation of concerns:
- Coordinator produces `Assignment`s.
- Simulation applies `Assignment`s and mutates `TaskState`.
- `Task` (definition) mutates `TaskState` when directed by the Simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from simulation_models.assignment import RobotId
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
