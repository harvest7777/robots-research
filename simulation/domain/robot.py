"""
Robot Execution Model

A Robot is a physical actor that executes movement and work.

This module separates:
- `Robot`: immutable robot definition (capabilities, speed)
- `RobotState`: mutable runtime state (position, battery)

State mutation is handled by free functions (`move_robot`, `work_robot`,
`idle_robot`) rather than methods on `Robot`, because `Robot` carries no
per-instance data that these operations depend on. The functions are named
explicitly to make call sites self-describing.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.primitives.capability import Capability
from simulation.primitives.position import Position
from simulation.domain.robot_state import RobotId, RobotState


# Battery drain rates (per tick)
_DRAIN_MOVE_PER_TICK = 0.001   # per tick of movement (1 cell)
_DRAIN_WORK_PER_TICK = 0.002   # per tick of work
_DRAIN_IDLE_PER_TICK = 0.0005  # per tick idle


@dataclass(frozen=True)
class Robot:
    """
    Immutable robot definition.

    Carries identity and capability data only. All state mutation is done
    by the free functions in this module.

    speed: cells moved per tick (each cell step is collision-checked separately).
    battery_drain_per_unit_of_movement: battery lost per one-cell move.
    battery_drain_per_unit_of_work_execution: battery lost per one-tick work contribution.
    battery_drain_per_tick_idle: battery lost when neither moving nor working.
    """

    id: RobotId
    capabilities: frozenset[Capability]
    speed: int = 1
    battery_drain_per_unit_of_movement:       float = _DRAIN_MOVE_PER_TICK
    battery_drain_per_unit_of_work_execution: float = _DRAIN_WORK_PER_TICK
    battery_drain_per_tick_idle:              float = _DRAIN_IDLE_PER_TICK


# ---------------------------------------------------------------------------
# State-mutation functions
# ---------------------------------------------------------------------------

def move_robot(state: RobotState, target: Position) -> None:
    """Move the robot to an adjacent cell and drain movement battery.

    The caller is responsible for ensuring `target` is exactly one
    cardinal step away and is not blocked.
    """
    object.__setattr__(state, "position", target)
    object.__setattr__(state, "battery_level", state.battery_level - _DRAIN_MOVE_PER_TICK)


def work_robot(state: RobotState) -> None:
    """Apply one tick of work effort and drain work battery.

    The robot does not know what task is being worked on.
    """
    object.__setattr__(state, "battery_level", state.battery_level - _DRAIN_WORK_PER_TICK)


def idle_robot(state: RobotState) -> None:
    """Apply one tick of idle drain."""
    object.__setattr__(state, "battery_level", state.battery_level - _DRAIN_IDLE_PER_TICK)
