"""
InMemoryAssignmentService: in-memory implementation of BaseAssignmentService.

Stores assignments in a plain list. Suitable for testing, CLI tools, and any
context where file-backed persistence is not needed.

Resolution behaviour is identical to JsonAssignmentService: for each robot,
the assignment with the highest assign_at still <= time wins.
"""

from __future__ import annotations

from services.base_assignment_service import BaseAssignmentService
from simulation.domain.assignment import Assignment
from simulation.primitives.time import Time


class InMemoryAssignmentService(BaseAssignmentService):
    def __init__(self, assignments: list[Assignment] | None = None) -> None:
        self._assignments: list[Assignment] = assignments or []

    def get_assignments_for_time(self, time: Time) -> list[Assignment]:
        all_robot_ids = {rid for a in self._assignments for rid in a.robot_ids}
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
