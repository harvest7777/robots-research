"""
BaseAssignmentService: abstract interface for assignment storage.

Consumers call get_assignments_for_time(t) to get the active assignments
at a given simulation time. The returned list is already resolved — one
winning Assignment per robot (highest assign_at still <= t).

Parsing the list into a robot→task mapping is the caller's responsibility.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from simulation_models.assignment import Assignment
from simulation_models.time import Time


class BaseAssignmentService(ABC):
    @abstractmethod
    def get_assignments_for_time(self, time: Time) -> list[Assignment]:
        """Return the active assignments at the given simulation time.

        For each robot, returns the assignment with the highest assign_at
        that is still <= time. Robots with no applicable assignment are
        omitted from the result.
        """

    @abstractmethod
    def set_assignments(self, assignments: list[Assignment]) -> None:
        """Replace all stored assignments with the given list.

        Use for initialization or a hard reset. Destroys previous history.
        """

    @abstractmethod
    def add_assignments(self, assignments: list[Assignment]) -> None:
        """Append assignments to the existing store.

        Does not remove existing assignments. Later assign_at values will
        override earlier ones when resolved via get_assignments_for_time.
        """
