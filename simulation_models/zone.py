"""
Zones (typed regions)

This module defines a single `Zone` type used to represent regions/areas in the
environment (inspection areas, charging stations, restricted areas, etc.).

Design constraints:
- A zone has a `ZoneType`.
- A zone may cover multiple grid positions.
- Covered positions are stored privately; callers can only query membership via
  `Zone.contains(pos)`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, NewType

from .position import Position

ZoneId = NewType("ZoneId", int)

class ZoneType(str, Enum):
    INSPECTION = "inspection"
    MAINTENANCE = "maintenance"
    LOADING = "loading"
    RESTRICTED = "restricted"
    CHARGING = "charging"


@dataclass(frozen=True)
class Zone:
    """
    A typed region containing one or more grid positions.

    Notes:
    - Covered positions are stored privately and should not be accessed directly.
    - Use `contains(pos)` to test whether a position is inside the zone.
    """

    id: ZoneId
    zone_type: ZoneType
    _positions: frozenset[Position]

    @staticmethod
    def from_positions(id: ZoneId, zone_type: ZoneType, positions: Iterable[Position]) -> "Zone":
        """Convenience constructor for building a zone from positions."""
        return Zone(id=id, zone_type=zone_type, _positions=frozenset(positions))

    def contains(self, pos: Position) -> bool:
        """Return True if this zone contains `pos`.

        Float positions are floored to the enclosing grid cell before lookup,
        so a robot at (3.74, 2.12) is inside the zone if cell (3, 2) is covered.
        """
        return Position(int(pos.x), int(pos.y)) in self._positions

    @property
    def cells(self) -> frozenset[Position]:
        """Return the positions covered by this zone."""
        return self._positions