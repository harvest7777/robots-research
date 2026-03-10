"""
StepContext

A lightweight bundle of the read-only simulation state slices that multiple
per-tick functions need. Avoids threading six-plus individual parameters
through every call site while keeping each function's dependencies explicit.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation_models.robot_state import RobotId
from simulation_models.environment import Environment
from simulation_models.robot_state import RobotState
from simulation_models.task import Task, TaskId
from simulation_models.task_state import TaskState
from simulation_models.time import Time


@dataclass
class StepContext:
    """Snapshot of simulation state for a single tick.

    Attributes:
        robot_states:  Mutable state for every robot, keyed by robot_id.
        task_states:   Mutable state for every task, keyed by task_id.
        robot_to_task: Active assignment map: robot_id → task_id.
        task_by_id:    Immutable task definitions, keyed by task_id.
        environment:   The grid environment (immutable during a step).
        t_now:         Current simulation time at the start of this tick.
    """

    robot_states: dict[RobotId, RobotState]
    task_states: dict[TaskId, TaskState]
    robot_to_task: dict[RobotId, TaskId]
    task_by_id: dict[TaskId, Task]
    environment: Environment
    t_now: Time
