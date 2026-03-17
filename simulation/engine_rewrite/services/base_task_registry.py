"""
BaseTaskRegistry

Abstract base class for the task registry. The registry is the authoritative
store of task definitions visible to the assigner. It has no opinion on task
status (that lives in StateService) or assignment (that's the assigner's job).

Implementations may back this with memory, JSON, a database, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from simulation.domain.base_task import BaseTask, TaskId


class BaseTaskRegistry(ABC):

    @abstractmethod
    def add(self, task: BaseTask) -> None:
        """Add a task to the registry."""

    @abstractmethod
    def all(self) -> list[BaseTask]:
        """Return every task in the registry."""

    @abstractmethod
    def get(self, task_id: TaskId) -> BaseTask | None:
        """Return the task with the given ID, or None if not found."""
