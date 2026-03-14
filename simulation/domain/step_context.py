"""
StepContext

A lightweight parameter bundle of simulation state slices that multiple
per-tick functions need. Avoids threading six-plus individual arguments
through every call site while keeping each function's dependencies explicit.

Note: robot_states and task_states are live references to the mutable dicts,
not copies. This is a bundle, not a snapshot.

The active assignments list is the single source of truth for robot-task
bindings within a tick. Algorithms that need a robot→task or task→robots
view derive it locally from this list rather than from a pre-computed dict,
keeping one canonical representation.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.domain.assignment import Assignment
from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
from simulation.domain.environment import Environment
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.primitives.time import Time


@dataclass
class StepContext:
    """Per-tick parameter bundle for simulation step functions.

    Attributes:
        robot_states:  Live mutable state for every robot, keyed by robot_id.
        task_states:   Live mutable state for every task, keyed by task_id.
        assignments:   Active assignments this tick — the single source of
                       truth for robot-task bindings. Use this to derive
                       robot→task or task→robots views as needed.
        robot_by_id:   Immutable robot definitions, keyed by robot_id.
        task_by_id:    Immutable task definitions, keyed by task_id.
        environment:   The grid environment (immutable during a step).
        t_now:         Current simulation time at the start of this tick.
    """

    robot_states: dict[RobotId, RobotState]
    task_states: dict[TaskId, BaseTaskState]
    assignments: list[Assignment]
    robot_by_id: dict[RobotId, Robot]
    task_by_id: dict[TaskId, BaseTask]
    environment: Environment
    t_now: Time
