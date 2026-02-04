"""
Assignment data objects.

An assignment represents current responsibility only:
"Robot R is responsible for Task T at this moment."

Assignments are:
- Ephemeral: produced by coordination algorithms, consumed immediately
- Immutable: never modified after creation
- Pure data: no logic, no validation, no behavior

Assignments contain NO execution state (no times, progress, status, history).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType

from simulation_models.task import TaskId

RobotId = NewType("RobotId", int)
"""Opaque identifier for robots. Hashable and comparable."""


@dataclass(frozen=True)
class Assignment:
    """
    Assignment of robot(s) to a task.

    Represents: "At this decision step, these robots should work on this task."
    Nothing more.
    """

    task_id: TaskId
    robot_ids: frozenset[RobotId]
