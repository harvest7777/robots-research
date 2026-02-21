"""
Environment (discrete grid world)

This module defines a minimal `Environment` backed by a 2D grid.

Coordinate / indexing conventions:
- Positions use `Position(x: float, y: float)`.
- `(0.0, 0.0)` is the **top-left** cell.
- `x` indexes columns (increases to the right).
- `y` indexes rows (increases downward).
- Grid indexing uses integer-floored coordinates: `grid[int(y)][int(x)]`.

Core invariant:
- **No overlap**: at most one object may occupy a grid cell at a time.
"""
from __future__ import annotations

from .position import Position
from .zone import Zone, ZoneId

class Obstacle:
    """Marker object representing an impassable obstacle on the grid."""

    def __str__(self) -> str:
        return "#"


class Environment:
    """Discrete grid environment enforcing no-overlap occupancy."""

    UNKNOWN_OBJECT_STRING = "?"
    """
    Placeholder rendered in `__repr__` when a grid cell contains an object that cannot
    be converted to a string (i.e., `str(obj)` raises).
    """

    def __init__(self, width: int, height: int):
        self._width = width    # cols
        self._height = height  # rows
        self._grid = [[None for _ in range(width)]
                      for _ in range(height)]
        self._zones: dict[ZoneId, Zone] = {}
        self._obstacles: set[Position] = set()

    @property
    def width(self) -> int:
        """Return the width (number of columns) of the environment."""
        return self._width

    @property
    def height(self) -> int:
        """Return the height (number of rows) of the environment."""
        return self._height

    def __repr__(self) -> str:
        """
        Return a human-readable representation of the environment grid.

        Assumptions:
        - Objects placed in the environment are "printable" (i.e., `str(obj)` works).

        Rendering rules:
        - Empty cells in a zone render as the zone ID (single digit, or `+` if ID >= 10).
        - Empty cells not in any zone render as `.`.
        - Occupied cells render as the first character of `str(obj)` to keep columns aligned.
        - If `str(obj)` fails for any reason, the cell renders as `UNKNOWN_OBJECT_STRING`
          (the literal `?`).
        """
        rows: list[str] = []
        for y in range(self._height):
            row_chars: list[str] = []
            for x in range(self._width):
                obj = self._grid[y][x]
                if obj is None:
                    pos = Position(float(x), float(y))
                    zone_id = self._get_zone_id_at(pos)
                    if zone_id is not None:
                        row_chars.append(str(zone_id) if zone_id < 10 else "+")
                    else:
                        row_chars.append(".")
                    continue
                try:
                    s = str(obj)
                    row_chars.append((s[0] if s else self.UNKNOWN_OBJECT_STRING))
                except Exception:
                    row_chars.append(self.UNKNOWN_OBJECT_STRING)
            rows.append("".join(row_chars))

        grid_str = "\n".join(rows)
        return f"Environment(width={self._width}, height={self._height})\n{grid_str}"

    def get_at(self, pos: Position) -> object | None:
        """
        Return the object stored at `pos` (or `None` if the cell is empty).

        This is a read-only query of the environment's internal grid representation:
        it does not mutate state.
        """
        if not self._position_in_bounds(pos):
            raise IndexError(f"Invalid position {pos}")
        cx, cy = self._cell(pos)
        return self._grid[cy][cx]

    def is_empty(self, pos: Position) -> bool:
        """
        Return True if the grid cell at `pos` contains no object.

        This is the inverse of occupancy for the cell and supports the environment
        invariant that objects cannot overlap (i.e., `place()` requires `is_empty()`).
        """
        return self.get_at(pos) is None

    def place(self, pos: Position, obj: object) -> None:
        """
        Place an object into the environment at `pos` by mutating the internal grid.

        Effects:
        - Validates `pos` is in-bounds.
        - Enforces the invariant that **no two objects may overlap**:
          if the target cell is already occupied, raises `ValueError`.
        - Otherwise writes `obj` into the backing grid cell.
        """
        if not self._position_in_bounds(pos):
            raise IndexError(f"Invalid position {pos}")
        cx, cy = self._cell(pos)
        if self._grid[cy][cx] is not None:
            raise ValueError("Position occupied")
        self._grid[cy][cx] = obj

    @property
    def obstacles(self) -> frozenset[Position]:
        """Return the set of obstacle positions."""
        return frozenset(self._obstacles)

    def add_obstacle(self, pos: Position) -> None:
        """
        Add an obstacle at the given position.

        Raises:
            IndexError: If position is out of bounds.
            ValueError: If position is already occupied.
        """
        if pos in self._obstacles:
            return  # Already an obstacle here, no-op
        self.place(pos, Obstacle())
        self._obstacles.add(pos)

    def add_zone(self, zone: Zone) -> None:
        """
        Add a Zone to the Environment while enforcing spatial invariants.

        Invariants enforced:
        - All zone cells must be within environment bounds.
        - Zones must not overlap with each other.

        This method is atomic: if any validation fails, the environment state
        remains unchanged.

        Raises:
            ValueError: If zone ID already exists or zones would overlap.
            IndexError: If any zone position is out of bounds.
        """
        # Step 1: Validate zone identity - reject duplicate zone IDs
        if zone.id in self._zones:
            raise ValueError(f"Zone with id {zone.id} already exists")

        # Step 2: Validate all zone positions are within bounds
        for pos in zone.cells:
            if not self._position_in_bounds(pos):
                raise IndexError(f"Zone position {pos} is out of bounds for zone id {zone.id}")

        # Step 3: Validate zones do not overlap with existing zones
        for existing_zone in self._zones.values():
            if zone.cells & existing_zone.cells:
                raise ValueError(
                    f"Zone {zone.id} overlaps with existing zone {existing_zone.id}"
                )

        # All validations passed - commit the zone
        self._zones[zone.id] = zone

    def in_bounds(self, pos: Position) -> bool:
        """Return True if `pos` is within the grid bounds."""
        return self._position_in_bounds(pos)

    def get_zone(self, zone_id: ZoneId) -> Zone | None:
        """Return the Zone with the given ID, or None if not found."""
        return self._zones.get(zone_id)

    def _cell(self, pos: Position) -> tuple[int, int]:
        """Convert a Position to integer grid cell indices (col, row)."""
        return (int(pos.x), int(pos.y))

    def _get_zone_id_at(self, pos: Position) -> ZoneId | None:
        """Return the zone ID containing `pos`, or None if not in any zone."""
        for zone_id, zone in self._zones.items():
            if zone.contains(pos):
                return zone_id
        return None

    def _position_in_bounds(self, pos: Position) -> bool:
        """
        Check whether a Position maps to a valid grid cell.

        Mapping convention:
        - The grid uses a top-left origin: `(0.0, 0.0)` is the top-left cell.
        - `pos.x` is the column index (increases to the right).
        - `pos.y` is the row index (increases downward).

        Returns True if the position is within grid bounds, False otherwise.
        """
        return 0 <= pos.x < self._width and 0 <= pos.y < self._height


if __name__ == "__main__":
    env = Environment(width=10, height=5)
    print(env)
