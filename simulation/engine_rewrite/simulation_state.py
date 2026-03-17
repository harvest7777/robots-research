"""
SimulationState (new design)

Immutable snapshot of all simulation data for one tick.
Passed into classify_step and apply_outcome — never mutated in place.
apply_outcome returns a new SimulationState each tick.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
from simulation.domain.environment import Environment
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.primitives.time import Time

from .assignment import Assignment


@dataclass(frozen=True)
class SimulationState:
    environment: Environment
    robots: dict[RobotId, Robot]
    robot_states: dict[RobotId, RobotState]
    tasks: dict[TaskId, BaseTask]
    task_states: dict[TaskId, BaseTaskState]
    t_now: Time = field(default_factory=lambda: Time(0))
    assignments: tuple[Assignment, ...] = ()
