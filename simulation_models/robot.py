"""
Robot Execution Model

A Robot is a physical actor that executes movement and work.

This module separates:
- `Robot`: immutable robot definition (capabilities, speed, radius)
- `RobotState`: mutable runtime state (position, battery)

The robot updates runtime state but:
- Does NOT own tasks
- Does NOT make decisions
- Does NOT enforce invariants

The robot is a dumb executor. All coordination lives in the Simulation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from simulation_models.assignment import RobotId
from simulation_models.capability import Capability
from simulation_models.position import Position
from simulation_models.robot_state import RobotState
from simulation_models.time import Time


# Battery drain rates (per tick)
_DRAIN_MOVE_PER_UNIT = 0.001  # per unit distance moved
_DRAIN_WORK_PER_TICK = 0.002  # per tick of work
_DRAIN_IDLE_PER_TICK = 0.0005  # per tick idle

# Guard against floating-point jitter when robot is at target
_AT_TARGET_EPSILON = 0.001


@dataclass(frozen=True)
class Robot:
    """
    Immutable robot definition + execution model.

    The robot:
    - Executes movement and work
    - Updates physical state via `RobotState` (position, battery)
    - Does NOT know what a task is
    - Does NOT decide what to work on

    All time deltas are passed as Time objects and treated as opaque units.
    """

    id: RobotId
    capabilities: frozenset[Capability]
    speed: float
    radius: float = field(default=0.4)

    def move_towards(self, state: RobotState, target: Position, dt: Time) -> None:
        """
        Move toward the target using continuous vector math.

        Direction is normalized; travel distance is clamped so the robot cannot
        overshoot the target. Updates position and drains battery on state.

        Does NOT check collisions or bounds.
        """
        dx = target.x - state.position.x
        dy = target.y - state.position.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < _AT_TARGET_EPSILON:
            return
        travel = min(self.speed * dt.tick, dist)
        nx = state.position.x + (dx / dist) * travel
        ny = state.position.y + (dy / dist) * travel
        state.position = Position(nx, ny)
        state.battery_level -= travel * _DRAIN_MOVE_PER_UNIT

    def work(self, state: RobotState, dt: Time) -> None:
        """
        Apply work effort for dt time units.

        The robot does NOT know:
        - What task is being worked on
        - Whether work completes anything

        Drains battery proportional to dt.
        """
        state.battery_level -= dt.tick * _DRAIN_WORK_PER_TICK

    def idle(self, state: RobotState, dt: Time) -> None:
        """
        Robot is idle for dt time units.

        Applies minimal idle battery drain.
        """
        state.battery_level -= dt.tick * _DRAIN_IDLE_PER_TICK
