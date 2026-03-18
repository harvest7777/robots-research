"""
Formation planner.

Pure functions for moving a rigid-body formation one step toward a destination.
No task or robot domain knowledge — inputs are plain Positions and an Environment.

The formation is a set of positions (task + eligible robots). Each tick the
Observer determines whether the formation is ready to move, then calls
plan_formation_move to get a (dx, dy) direction. The entire formation shifts
by that offset as one unit.
"""

from __future__ import annotations

from collections.abc import Iterable

from simulation.domain.environment import Environment
from simulation.primitives.position import Position

# Cardinal directions ordered: right, left, down, up.
# plan_formation_move filters and re-sorts these by progress toward the
# destination, so the raw order here is just a stable tiebreak.
_DIRECTIONS: list[tuple[int, int]] = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def is_formation_clear(
    positions: Iterable[Position],
    environment: Environment,
    occupied: frozenset[Position],
) -> bool:
    """Return True if every position is in-bounds, obstacle-free, and not occupied."""
    for pos in positions:
        if not environment.in_bounds(pos):
            return False
        if pos in environment.obstacles:
            return False
        if pos in occupied:
            return False
    return True


def plan_formation_move(
    formation: frozenset[Position],
    destination: Position,
    environment: Environment,
    occupied: frozenset[Position],
    task_position: Position | None = None,
) -> tuple[int, int] | None:
    """Return a (dx, dy) that moves the formation one step toward destination.

    Tries cardinal directions that reduce the Manhattan distance from the
    task toward the destination. Directions are sorted by how much they
    reduce that distance (most reduction first). Returns the first direction
    whose shifted formation passes is_formation_clear, or None if all
    directions are blocked or the task is already at the destination.

    Args:
        task_position: The position of the task object within the formation.
            When provided, progress is measured from the task to the
            destination rather than from the nearest formation member.
            This prevents robots that drift onto the destination cell from
            prematurely halting the formation. Falls back to formation-wide
            minimum when None.
    """
    if not formation:
        return None

    # Track progress from the task position when known; fall back to the
    # formation-wide minimum for backward compatibility.
    _ref = task_position if task_position is not None else None
    current_min = (
        _ref.manhattan(destination)
        if _ref is not None
        else min(pos.manhattan(destination) for pos in formation)
    )
    if current_min == 0:
        return None

    def _progress(direction: tuple[int, int]) -> int:
        dx, dy = direction
        if _ref is not None:
            new_min = Position(_ref.x + dx, _ref.y + dy).manhattan(destination)
        else:
            new_min = min(
                Position(pos.x + dx, pos.y + dy).manhattan(destination)
                for pos in formation
            )
        return current_min - new_min  # positive = makes progress

    candidates = sorted(
        [d for d in _DIRECTIONS if _progress(d) > 0],
        key=_progress,
        reverse=True,
    )

    for dx, dy in candidates:
        shifted = frozenset(Position(pos.x + dx, pos.y + dy) for pos in formation)
        if is_formation_clear(shifted, environment, occupied):
            return dx, dy

    return None
