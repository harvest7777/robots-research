"""
Robot Execution Model

A Robot is a physical actor that executes movement and work.

This module separates:
- `Robot`: immutable robot definition (capabilities, speed)
- `RobotState`: mutable runtime state (position, battery)

The robot updates runtime state but:
- Does NOT own tasks
- Does NOT make decisions
- Does NOT enforce invariants

The robot is a dumb executor. All coordination lives in the Simulation.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation_models.capability import Capability
from simulation_models.position import Position
from simulation_models.robot_state import RobotId, RobotState


# Battery drain rates (per tick)
_DRAIN_MOVE_PER_TICK = 0.001   # per tick of movement (1 cell)
_DRAIN_WORK_PER_TICK = 0.002   # per tick of work
_DRAIN_IDLE_PER_TICK = 0.0005  # per tick idle


@dataclass(frozen=True)
class Robot:
    """
    Immutable robot definition + execution model.

    The robot:
    - Executes movement and work
    - Updates physical state via `RobotState` (position, battery)
    - Does NOT know what a task is
    - Does NOT decide what to work on

    speed: cells moved per tick (each cell step is collision-checked separately).
    """

    id: RobotId
    capabilities: frozenset[Capability]
    speed: int = 1

    def step_to(self, state: RobotState, target: Position) -> None:
        """
        Teleport robot to an adjacent cell.

        The caller is responsible for ensuring `target` is exactly one
        cardinal step away and is not blocked. Drains battery for movement.
        """
        state.position = target
        state.battery_level -= _DRAIN_MOVE_PER_TICK

    def work(self, state: RobotState) -> None:
        """
        Apply one tick of work effort. Drains battery.

        The robot does NOT know what task is being worked on.
        """
        state.battery_level -= _DRAIN_WORK_PER_TICK

    def idle(self, state: RobotState) -> None:
        """
        Robot is idle for one tick. Applies minimal battery drain.
        """
        state.battery_level -= _DRAIN_IDLE_PER_TICK
