from dataclasses import dataclass

from simulation import BaseTask
from simulation.primitives import Time
@dataclass
class SpawnTask:
    """
    Wrapper around task with a time to spawn, defaults to Time 0.
    Useful for pre-defining tasks to stream in.
    """
    task_to_spawn: BaseTask
    time_to_spawn: Time = Time(0)
