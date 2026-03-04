"""
InMemoryAssignmentService: in-memory implementation of BaseAssignmentService.
"""

from __future__ import annotations

from simulation_models.assignment import Assignment, RobotId
from simulation_models.time import Time
from services.base_assignment_service import BaseAssignmentService


class InMemoryAssignmentService(BaseAssignmentService):
    def __init__(self) -> None:
        self._assignments: list[Assignment] = []

    def get_assignments_for_time(self, time: Time) -> list[Assignment]:
        all_robot_ids: set[RobotId] = {
            rid for a in self._assignments for rid in a.robot_ids
        }
        seen: set[Assignment] = set()
        for robot_id in all_robot_ids:
            applicable = [
                a for a in self._assignments
                if robot_id in a.robot_ids and a.assign_at.tick <= time.tick
            ]
            if applicable:
                seen.add(max(applicable, key=lambda a: a.assign_at.tick))
        return list(seen)

    def set_assignments(self, assignments: list[Assignment]) -> None:
        self._assignments = list(assignments)

    def add_assignments(self, assignments: list[Assignment]) -> None:
        self._assignments.extend(assignments)
