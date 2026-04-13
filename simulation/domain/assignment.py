"""
Assignment

A flat, stateless binding of one robot to one task.
No timestamp, no grouping — just the pair.

The AssignmentService holds the full set of current assignments.
The runner replaces the set on each re-assignment trigger.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.domain.base_task import TaskId
from simulation.domain.robot_state import RobotId


@dataclass(frozen=True)
class Assignment:
    task_id: TaskId
    robot_id: RobotId

    def to_json_dict(self) -> dict:
        return {"robot_id": int(self.robot_id), "task_id": int(self.task_id)}
