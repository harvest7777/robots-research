"""
BaseAssignmentService

Abstract base class for the assignment service. Holds one assignment per robot,
keyed by robot ID. The assigner calls update() to upsert assignments; the runner
calls get_current() each tick to read them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from simulation.engine_rewrite.assignment import Assignment


class BaseAssignmentService(ABC):

    @abstractmethod
    def get_current(self) -> list[Assignment]:
        """Return all current assignments (one per robot)."""

    @abstractmethod
    def update(self, assignments: list[Assignment]) -> None:
        """Upsert assignments by robot ID. Existing robots not in the list are unchanged."""
