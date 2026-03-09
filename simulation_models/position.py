"""
Grid coordinate conventions

- Positions use integer grid cell coordinates (x: int, y: int).
- The origin is the top-left cell: (0, 0).
- x increases to the right (column index).
- y increases downward (row index).

Robots always occupy exactly one grid cell. There are no sub-cell positions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    """Immutable integer grid cell coordinate."""
    x: int
    y: int

    def manhattan(self, other: "Position") -> int:
        """Return the Manhattan distance to another position."""
        return abs(self.x - other.x) + abs(self.y - other.y)
