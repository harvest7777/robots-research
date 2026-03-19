"""
InMemoryTaskRegistry

.. deprecated::
    Use ``InMemorySimulationRegistry`` instead.  This class only holds task
    definitions; ``InMemorySimulationRegistry`` holds both task *and* robot
    definitions, which is what the runner and services expect.

    This class will be removed in a future cleanup pass once all callers have
    migrated.
"""

from __future__ import annotations

from simulation.domain.base_task import BaseTask, TaskId

from .base_task_registry import BaseTaskRegistry


class InMemoryTaskRegistry(BaseTaskRegistry):

    def __init__(self, tasks: list[BaseTask] | None = None) -> None:
        self._tasks: dict[TaskId, BaseTask] = {}
        for task in (tasks or []):
            self._tasks[task.id] = task

    def add(self, task: BaseTask) -> None:
        self._tasks[task.id] = task

    def all(self) -> list[BaseTask]:
        return list(self._tasks.values())

    def get(self, task_id: TaskId) -> BaseTask | None:
        return self._tasks.get(task_id)
