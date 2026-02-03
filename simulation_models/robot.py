"""
Robot Execution Model

A Robot is a physical actor that executes movement and work.
It updates its own physical state (position, battery) but:
- Does NOT own tasks
- Does NOT make decisions
- Does NOT enforce invariants

The robot is a dumb executor. All coordination lives in the Simulation.
"""

import math

from simulation_models.assignment import RobotId
from simulation_models.capability import Capability
from simulation_models.position import Position
from simulation_models.time import Time


# Battery drain rates (per tick)
_DRAIN_MOVE_PER_UNIT = 0.001  # per unit distance moved
_DRAIN_WORK_PER_TICK = 0.002  # per tick of work
_DRAIN_IDLE_PER_TICK = 0.0005  # per tick idle


class Robot:
    """
    A physical actor that executes actions.

    The robot:
    - Executes movement and work
    - Updates physical state (position, battery)
    - Does NOT know what a task is
    - Does NOT decide what to work on

    All time deltas are passed as Time objects and treated as opaque units.
    """

    def __init__(
        self,
        id: RobotId,
        position: Position,
        capabilities: frozenset[Capability],
        speed: float,
        battery_level: float = 1.0,
    ) -> None:
        self._id = id
        self._x = float(position.x)
        self._y = float(position.y)
        self._capabilities = capabilities
        self._speed = speed
        self._battery_level = battery_level

    @property
    def id(self) -> RobotId:
        return self._id

    @property
    def position(self) -> Position:
        """Current position as discrete grid coordinates."""
        return Position(int(self._x), int(self._y))

    @property
    def battery_level(self) -> float:
        return self._battery_level

    @property
    def capabilities(self) -> frozenset[Capability]:
        return self._capabilities

    @property
    def speed(self) -> float:
        return self._speed

    def move_towards(self, target: Position, dt: Time) -> None:
        """
        Move in a straight line toward the target.

        Distance moved is proportional to speed * dt.
        Updates position and drains battery.

        Does NOT check collisions or bounds.
        """
        dx = target.x - self._x
        dy = target.y - self._y
        distance_to_target = math.sqrt(dx * dx + dy * dy)

        if distance_to_target == 0:
            return

        max_distance = self._speed * dt.tick

        if distance_to_target <= max_distance:
            # Close enough to reach target
            self._x = float(target.x)
            self._y = float(target.y)
            distance_moved = distance_to_target
        else:
            # Move towards target by max_distance
            ratio = max_distance / distance_to_target
            self._x += dx * ratio
            self._y += dy * ratio
            distance_moved = max_distance

        self._battery_level -= distance_moved * _DRAIN_MOVE_PER_UNIT

    def work(self, dt: Time) -> None:
        """
        Apply work effort for dt time units.

        The robot does NOT know:
        - What task is being worked on
        - Whether work completes anything

        Drains battery proportional to dt.
        """
        self._battery_level -= dt.tick * _DRAIN_WORK_PER_TICK

    def idle(self, dt: Time) -> None:
        """
        Robot is idle for dt time units.

        Applies minimal idle battery drain.
        """
        self._battery_level -= dt.tick * _DRAIN_IDLE_PER_TICK
