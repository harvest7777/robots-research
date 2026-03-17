"""
InMemoryAssignmentService

In-memory implementation of BaseAssignmentService.
"""

from __future__ import annotations

from simulation.engine_rewrite.assignment import Assignment

from .base_assignment_service import BaseAssignmentService


class InMemoryAssignmentService(BaseAssignmentService):

    def __init__(self, assignments: list[Assignment] | None = None) -> None:
        self._assignments: list[Assignment] = list(assignments or [])

    def get_current(self) -> list[Assignment]:
        return list(self._assignments)

    def set(self, assignments: list[Assignment]) -> None:
        self._assignments = list(assignments)
