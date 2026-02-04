"""
Simulation Time

Time is an opaque value object representing a point or duration in simulation time.
It is internally backed by an integer tick count but should be treated as opaque.

Do NOT convert Time to floats, seconds, or wall-clock time.
Do NOT assume real-world units.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Time:
    """
    Immutable value object representing a point or duration in simulation time.

    This is a pure value type with no scheduling or execution logic.
    """

    tick: int

    def advance(self, dt: "Time") -> "Time":
        return Time(self.tick + dt.tick)

