"""
BaseTaskRegistry

.. deprecated::
    Use ``BaseSimulationRegistry`` instead.  ``BaseTaskRegistry`` only held
    task definitions; ``BaseSimulationRegistry`` holds both task *and* robot
    definitions, which is what the runner and services expect.

    This class will be removed in a future cleanup pass once all callers have
    migrated.
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod

from simulation.domain.base_task import BaseTask, TaskId


class BaseTaskRegistry(ABC):
    """Deprecated: use BaseSimulationRegistry."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__name__ != "InMemoryTaskRegistry":
            warnings.warn(
                f"{cls.__name__} subclasses BaseTaskRegistry which is deprecated; "
                "use BaseSimulationRegistry instead.",
                DeprecationWarning,
                stacklevel=2,
            )

    @abstractmethod
    def add(self, task: BaseTask) -> None:
        """Add a task to the registry."""

    @abstractmethod
    def all(self) -> list[BaseTask]:
        """Return every task in the registry."""

    @abstractmethod
    def get(self, task_id: TaskId) -> BaseTask | None:
        """Return the task with the given ID, or None if not found."""
