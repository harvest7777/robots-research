"""
StepContext

A lightweight parameter bundle of simulation state slices that multiple
per-tick functions need. Avoids threading six-plus individual arguments
through every call site while keeping each function's dependencies explicit.

Note: robot_states and task_states are live references to the mutable dicts,
not copies. This is a bundle, not a snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.domain.environment import Environment
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.task import Task, TaskId
from simulation.domain.task_state import TaskState
from simulation.primitives.time import Time


@dataclass
class StepContext:
    """Per-tick parameter bundle for simulation step functions.

    Attributes:
        robot_states:  Live mutable state for every robot, keyed by robot_id.
        task_states:   Live mutable state for every task, keyed by task_id.
        robot_to_task: Active assignment map: robot_id → task_id.
        robot_by_id:   Immutable robot definitions, keyed by robot_id.
        task_by_id:    Immutable task definitions, keyed by task_id.
        environment:   The grid environment (immutable during a step).
        t_now:         Current simulation time at the start of this tick.
    """

    robot_states: dict[RobotId, RobotState]
    task_states: dict[TaskId, TaskState]
    robot_to_task: dict[RobotId, TaskId]
    robot_by_id: dict[RobotId, Robot]
    task_by_id: dict[TaskId, Task]
    environment: Environment
    t_now: Time
