"""
BaseAssignmentService

Abstract base class for the assignment service. Holds the current set of
robot-to-task assignments. The assigner writes to it; the runner reads from it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from simulation.engine_rewrite.assignment import Assignment


class BaseAssignmentService(ABC):

    @abstractmethod
    def get_current(self) -> list[Assignment]:
        """Return the current set of assignments."""

    @abstractmethod
    def set(self, assignments: list[Assignment]) -> None:
        """Replace the current set of assignments."""
