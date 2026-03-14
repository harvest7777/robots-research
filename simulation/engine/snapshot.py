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

Note: State objects within the snapshot are copies but remain technically
mutable dataclasses. Modifying them will not affect the live simulation,
but callers should treat them as read-only by convention.

Search state (rescue_found) is available via task_states: cast the
SearchTaskState entry for the relevant search task id.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from simulation.domain.assignment import Assignment
    from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
    from simulation.domain.environment import Environment
    from simulation.domain.robot import Robot
    from simulation.domain.robot_state import RobotId, RobotState
    from simulation.primitives.time import Time


@dataclass(frozen=True)
class SimulationSnapshot:
    """
    Immutable, point-in-time view of simulation state.

    Attributes:
        env: The environment (grid, zones, obstacles).
        robots: Tuple of robot definitions (immutable).
        robot_states: Read-only mapping of robot ID to runtime state (copies).
        tasks: Tuple of task definitions (immutable — Task or SearchTask).
        task_states: Read-only mapping of task ID to runtime state (copies).
                     SearchTaskState entries carry rescue_found for search tasks.
        t_now: Current simulation time at the moment of the snapshot.
        active_assignments: Active assignments at this tick.
    """

    env: "Environment"
    robots: "tuple[Robot, ...]"
    robot_states: "Mapping[RobotId, RobotState]"
    tasks: "tuple[BaseTask, ...]"
    task_states: "Mapping[TaskId, BaseTaskState]"
    t_now: "Time"
    active_assignments: "tuple[Assignment, ...]" = ()
