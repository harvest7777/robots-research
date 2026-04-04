from dataclasses import dataclass, field

from simulation import BaseTask, BaseTaskState, TaskState
from simulation.primitives import Time


@dataclass
class SpawnTask:
    """
    Wrapper around task with a time to spawn, defaults to Time 0.
    Useful for pre-defining tasks to stream in.
    """
    task_to_spawn: BaseTask
    time_to_spawn: Time = Time(0)
    task_state: BaseTaskState | None = field(default=None)

    def __post_init__(self):
        if self.task_state is None:
            self.task_state = TaskState(self.task_to_spawn)
