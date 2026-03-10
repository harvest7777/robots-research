"""
Read-only snapshot of simulation state.

This module provides `SimulationSnapshot`, an immutable point-in-time view of
the simulation state. The view layer should depend only on snapshots, not on
the live `Simulation` object.

Immutability guarantees:
- `SimulationSnapshot` is a frozen dataclass.
- Robot and task lists are tuples (immutable sequences).
- State mappings are wrapped in `MappingProxyType` (read-only dict views).
- State objects are copies, isolated from the live simulation.

Note: `RobotState` and `TaskState` objects within the snapshot are copies but
remain technically mutable dataclasses. Modifying them will not affect the live
simulation, but callers should treat them as read-only by convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from simulation.domain.assignment import Assignment
    from simulation.domain.environment import Environment
    from simulation.domain.rescue_point import RescuePointId
    from simulation.domain.robot import Robot
    from simulation.domain.robot_state import RobotId, RobotState
    from simulation.domain.task import Task, TaskId
    from simulation.domain.task_state import TaskState
    from simulation.primitives.time import Time


@dataclass(frozen=True)
class SimulationSnapshot:
    """
    Immutable, point-in-time view of simulation state.

    This snapshot captures the complete state of a simulation at a specific moment.
    It is designed for read-only consumption by view layers, analytics, or logging.

    Attributes:
        env: The environment (grid, zones, obstacles).
        robots: Tuple of robot definitions (immutable).
        robot_states: Read-only mapping of robot ID to runtime state (copies).
        tasks: Tuple of task definitions (immutable).
        task_states: Read-only mapping of task ID to runtime state (copies).
        t_now: Current simulation time at the moment of the snapshot.
    """

    env: "Environment"
    robots: tuple["Robot", ...]
    robot_states: Mapping["RobotId", "RobotState"]
    tasks: tuple["Task", ...]
    task_states: Mapping["TaskId", "TaskState"]
    t_now: "Time"
    active_assignments: tuple["Assignment", ...] = ()
    rescue_found: Mapping["RescuePointId", bool] = field(default_factory=dict)
