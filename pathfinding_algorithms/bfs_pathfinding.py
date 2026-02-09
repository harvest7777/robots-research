"""
BFS pathfinding algorithm.

Returns the next step on the shortest path from start to goal,
avoiding obstacles and occupied positions.
"""

from __future__ import annotations

from collections import deque

from simulation_models.environment import Environment
from simulation_models.position import Position


def bfs_pathfind(
    environment: Environment,
    start: Position,
    goal: Position,
    occupied: frozenset[Position],
) -> Position | None:
    """Find the next step on the shortest path from start to goal.

    Uses breadth-first search over the 4-connected grid, treating obstacles
    and occupied positions as impassable.

    Args:
        environment: The grid environment (provides bounds and obstacles).
        start: Current position.
        goal: Target position.
        occupied: Positions occupied by other robots (impassable).

    Returns:
        The next adjacent Position on the shortest path, or None if
        the goal is unreachable. If start == goal, returns start.
    """
    if start == goal:
        return start

    obstacles = environment.obstacles

    visited: set[Position] = {start}
    # Each queue entry is (position, first_step) where first_step is the
    # neighbor of start that begins this path.
    queue: deque[tuple[Position, Position]] = deque()

    for neighbor in _neighbors(start):
        if not environment.in_bounds(neighbor):
            continue
        if neighbor in obstacles or neighbor in occupied:
            continue
        if neighbor == goal:
            return neighbor
        visited.add(neighbor)
        queue.append((neighbor, neighbor))

    while queue:
        current, first_step = queue.popleft()
        for neighbor in _neighbors(current):
            if neighbor in visited:
                continue
            if not environment.in_bounds(neighbor):
                continue
            if neighbor in obstacles or neighbor in occupied:
                continue
            if neighbor == goal:
                return first_step
            visited.add(neighbor)
            queue.append((neighbor, first_step))

    return None


def _neighbors(pos: Position) -> list[Position]:
    """Return the 4-connected neighbors of a position."""
    return [pos.up, pos.down, pos.left, pos.right]
