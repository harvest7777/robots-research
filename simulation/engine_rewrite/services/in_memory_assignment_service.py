"""
InMemoryAssignmentService

In-memory implementation of BaseAssignmentService.
Stores one assignment per robot in a dict keyed by RobotId.
"""

from __future__ import annotations

from simulation.domain.robot_state import RobotId
from simulation.engine_rewrite.assignment import Assignment

from .base_assignment_service import BaseAssignmentService


class InMemoryAssignmentService(BaseAssignmentService):

    def __init__(self, assignments: list[Assignment] | None = None) -> None:
        self._assignments: dict[RobotId, Assignment] = {}
        for assignment in (assignments or []):
            self._assignments[assignment.robot_id] = assignment

    def get_current(self) -> list[Assignment]:
        return list(self._assignments.values())

    def update(self, assignments: list[Assignment]) -> None:
        for assignment in assignments:
            self._assignments[assignment.robot_id] = assignment

    def unassign(self, robot_id: RobotId) -> None:
        self._assignments.pop(robot_id, None)
