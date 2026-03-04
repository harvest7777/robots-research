"""
Assignment data objects.

An assignment represents a scheduled robot-task binding with a start time:
"From assign_at onwards, these robots are responsible for this task —
until a newer assignment for the same robot supersedes it."

The simulation resolves each robot's active assignment each tick by taking
the assignment with the highest assign_at that is still <= t_now.
Robots stay on their assigned task indefinitely until overridden.

Assignments are:
- Immutable: never modified after creation
- Pure data: no logic, no validation, no behavior
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NewType

from simulation_models.task import TaskId
from simulation_models.time import Time

RobotId = NewType("RobotId", int)
"""Opaque identifier for robots. Hashable and comparable."""


@dataclass(frozen=True)
class Assignment:
    """
    Scheduled assignment of robot(s) to a task.

    From assign_at onwards, the listed robots are responsible for task_id.
    A robot stays on this task until a newer assignment (higher assign_at,
    still <= t_now) overrides it.
    """

    task_id: TaskId
    robot_ids: frozenset[RobotId]
    assign_at: Time = field(default_factory=lambda: Time(0))
