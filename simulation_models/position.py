from dataclasses import dataclass


"""
Grid coordinate conventions

- Positions are discrete grid coordinates: **integers only** (`x: int`, `y: int`).
- The origin is the **top-left** cell: `(0, 0)`.
- `x` increases to the right.
- `y` increases downward.

Therefore:
- **up** means `y - 1`
- **down** means `y + 1`
- **left** means `x - 1`
- **right** means `x + 1`
"""


@dataclass(frozen=True)
class Position:
    """Immutable integer grid coordinate."""
    x: int
    y: int

    @property
    def up(self) -> "Position":
        """One cell up (decrement `y`)."""
        return Position(self.x, self.y - 1)

    @property
    def down(self) -> "Position":
        """One cell down (increment `y`)."""
        return Position(self.x, self.y + 1)

    @property
    def left(self) -> "Position":
        """One cell left (decrement `x`)."""
        return Position(self.x - 1, self.y)

    @property
    def right(self) -> "Position":
        """One cell right (increment `x`)."""
        return Position(self.x + 1, self.y)

if __name__ == "__main__":
    pos = Position(2, 3)
    print(pos.up)