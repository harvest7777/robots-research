from dataclasses import dataclass, field

from simulation import BaseTask, TaskState
from simulation.primitives import Time
@dataclass
class SpawnTask:
    """
    Wrapper around task with a time to spawn, defaults to Time 0.
    Useful for pre-defining tasks to stream in.
    """
    task_to_spawn: BaseTask
    time_to_spawn: Time = Time(0)
    task_state: TaskState = field(init=False)

    def __post_init__(self):
        self.task_state = TaskState(self.task_to_spawn)
