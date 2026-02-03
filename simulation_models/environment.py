"""
Environment (discrete grid world)

This module defines a minimal `Environment` backed by a 2D grid.

Coordinate / indexing conventions:
- Positions use `Position(x: int, y: int)` (integers only).
- `(0, 0)` is the **top-left** cell.
- `x` indexes columns (increases to the right).
- `y` indexes rows (increases downward).
- Grid indexing is `grid[y][x]`.

Core invariant:
- **No overlap**: at most one object may occupy a grid cell at a time.
"""
from .position import Position

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

    def __repr__(self) -> str:
        """
        Return a human-readable representation of the environment grid.

        Assumptions:
        - Objects placed in the environment are "printable" (i.e., `str(obj)` works).

        Rendering rules:
        - Empty cells render as `.`.
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
        self._validate_position(pos)
        return self._grid[pos.y][pos.x]

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
        - Otherwise writes `obj` into the backing grid cell: `self._grid[y][x] = obj`.
        """
        self._validate_position(pos)
        if self._grid[pos.y][pos.x] is not None:
            raise ValueError("Position occupied")
        self._grid[pos.y][pos.x] = obj

    def _validate_position(self, pos: Position) -> None:
        """
        Validate that a `Position` maps to a valid grid cell.

        Mapping convention:
        - The grid uses a top-left origin: `(0, 0)` is the top-left cell.
        - `pos.x` is the column index (increases to the right).
        - `pos.y` is the row index (increases downward).

        This method uses that mapping and checks the resulting `(row=y, col=x)`
        is in-bounds for the environment grid.
        """
        if not (0 <= pos.x < self._width and 0 <= pos.y < self._height):
            raise IndexError(f"Invalid position {pos}")


if __name__ == "__main__":
    env = Environment(width=10, height=5)
    print(env)
