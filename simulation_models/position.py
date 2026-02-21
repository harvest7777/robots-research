"""
Grid coordinate conventions

- Positions use continuous float coordinates (x: float, y: float).
- The origin is the top-left: (0.0, 0.0).
- x increases to the right.
- y increases downward.

Integer-valued floats like Position(3.0, 2.0) are used for grid cell origins
(obstacles, zones, task targets). Arbitrary floats like Position(3.74, 2.12)
are used for robot positions mid-movement.

Python guarantees hash(5) == hash(5.0) and 5 == 5.0, so frozen dataclass
set/dict membership works correctly across integer and float contexts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    """Immutable continuous coordinate (float x, y)."""
    x: float
    y: float

    def distance(self, other: "Position") -> float:
        """Return the Euclidean distance to another position."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def near(self, other: "Position", eps: float = 0.1) -> bool:
        """Return True if within eps Euclidean distance of other."""
        return self.distance(other) < eps


if __name__ == "__main__":
    pos = Position(2.0, 3.0)
    print(pos.distance(Position(5.0, 7.0)))
