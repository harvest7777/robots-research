from __future__ import annotations

from simulation.domain import SearchTask, TaskId
from simulation.domain.base_task import BaseTask, BaseTaskState
from simulation.domain.search_task import SearchTaskState
from simulation.primitives import Capability

SEARCH_TASK_ID = TaskId(1)

TASKS: dict[TaskId, BaseTask] = {
    SEARCH_TASK_ID: SearchTask(
        id=SEARCH_TASK_ID,
        priority=5,
        required_capabilities=frozenset({Capability.VISION}),
    )
}

TASK_STATES: dict[TaskId, BaseTaskState] = {
    SEARCH_TASK_ID: SearchTaskState(task_id=SEARCH_TASK_ID),
}
