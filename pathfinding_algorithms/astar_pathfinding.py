"""
A* pathfinding algorithm with 4-connectivity (cardinal directions only).

Returns the next step on the shortest path from start to goal,
avoiding obstacles. Robots always occupy integer grid cells and move
one cell per tick in N/S/E/W directions only.
"""

from __future__ import annotations

import heapq

from simulation.world.environment import Environment
from simulation.primitives.position import Position


def astar_pathfind(
    environment: Environment,
    start: Position,
    goal: Position,
) -> Position | None:
    """Find the next step on the shortest path from start to goal.

    Uses A* over the 4-connected grid with Manhattan distance heuristic.
    Treats obstacle cells as impassable.

    Args:
        environment: The grid environment (provides bounds and obstacles).
        start: Current robot position (integer grid cell).
        goal: Target position (integer grid cell).

    Returns:
        The next Position (adjacent grid cell) on the shortest path, or None
        if the goal is unreachable. Returns goal if start already equals goal.
    """
    if start == goal:
        return goal

    obstacle_cells: frozenset[tuple[int, int]] = frozenset(
        (p.x, p.y) for p in environment.obstacles
    )

    start_cell = (start.x, start.y)
    goal_cell = (goal.x, goal.y)

    if start_cell in obstacle_cells:
        return None

    width = environment.width
    height = environment.height

    def h(cell: tuple[int, int]) -> int:
        return abs(cell[0] - goal_cell[0]) + abs(cell[1] - goal_cell[1])

    # Priority queue entries: (f, g, cell, first_step)
    # first_step tracks which neighbor of start begins this path
    open_heap: list[tuple[int, int, tuple[int, int], tuple[int, int]]] = []
    came_first: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], int] = {start_cell: 0}

    for nx, ny in _neighbors(start_cell, width, height):
        if (nx, ny) in obstacle_cells and (nx, ny) != goal_cell:
            continue
        if (nx, ny) == goal_cell:
            return Position(nx, ny)
        g = 1
        f = g + h((nx, ny))
        heapq.heappush(open_heap, (f, g, (nx, ny), (nx, ny)))
        g_score[(nx, ny)] = g
        came_first[(nx, ny)] = (nx, ny)

    visited: set[tuple[int, int]] = {start_cell}

    while open_heap:
        f, g, current, first_step = heapq.heappop(open_heap)

        if current in visited:
            continue
        visited.add(current)

        if current == goal_cell:
            return Position(first_step[0], first_step[1])

        for nx, ny in _neighbors(current, width, height):
            if (nx, ny) in visited:
                continue
            if (nx, ny) in obstacle_cells and (nx, ny) != goal_cell:
                continue
            new_g = g + 1
            if (nx, ny) not in g_score or new_g < g_score[(nx, ny)]:
                g_score[(nx, ny)] = new_g
                new_f = new_g + h((nx, ny))
                step = came_first.get(current, first_step)
                came_first[(nx, ny)] = step
                heapq.heappush(open_heap, (new_f, new_g, (nx, ny), step))

    return None


def _neighbors(
    cell: tuple[int, int],
    width: int,
    height: int,
) -> list[tuple[int, int]]:
    """Return valid 4-connected (cardinal) neighbors within bounds."""
    cx, cy = cell
    candidates = [
        (cx + 1, cy),
        (cx - 1, cy),
        (cx,     cy + 1),
        (cx,     cy - 1),
    ]
    return [(nx, ny) for nx, ny in candidates if 0 <= nx < width and 0 <= ny < height]
