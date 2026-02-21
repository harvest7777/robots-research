"""
A* pathfinding algorithm with 8-connectivity.

Returns the next step on the shortest path from start to goal,
avoiding obstacles and occupied positions.

Improvements over BFS:
- 8-connected grid (diagonal movement allowed)
- Euclidean heuristic for shorter, more direct paths
- Obstacle inflation: adjacent cells of obstacles are blocked to prevent
  robot bodies (radius 0.4) from clipping obstacle edges
"""

from __future__ import annotations

import heapq
import math

from simulation_models.environment import Environment
from simulation_models.position import Position


def astar_pathfind(
    environment: Environment,
    start: Position,
    goal: Position,
    occupied: frozenset[Position],
) -> Position | None:
    """Find the next step on the shortest path from start to goal.

    Uses A* over the 8-connected grid with Euclidean distance heuristic.
    Treats obstacles, inflated obstacle neighbors, and occupied positions
    as impassable.

    Args:
        environment: The grid environment (provides bounds and obstacles).
        start: Current position (may be a float position mid-cell).
        goal: Target position (grid cell center).
        occupied: Positions occupied by other robots (impassable).

    Returns:
        The next Position (grid cell center) on the shortest path, or None if
        the goal is unreachable. Returns goal if start is already near goal.
    """
    start_cell = (int(start.x), int(start.y))
    goal_cell = (int(goal.x), int(goal.y))

    if start_cell == goal_cell:
        return goal

    # Build blocked set from obstacles (integer cells)
    obstacle_cells: set[tuple[int, int]] = {
        (int(p.x), int(p.y)) for p in environment.obstacles
    }

    # Inflate obstacles: 4-connected neighbors of obstacle cells are also blocked
    # (prevents robot body with radius 0.4 from clipping obstacle AABB edges)
    inflated: set[tuple[int, int]] = set()
    for (ox, oy) in obstacle_cells:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = (ox + dx, oy + dy)
            if neighbor not in obstacle_cells:
                inflated.add(neighbor)

    # Build occupied set from robot positions (integer cells)
    occupied_cells: set[tuple[int, int]] = {
        (int(p.x), int(p.y)) for p in occupied
    }

    # Blocked = obstacles + inflated (but never block the goal itself)
    blocked = obstacle_cells | (inflated - {goal_cell})
    blocked |= occupied_cells

    # If start is blocked (shouldn't happen, but handle gracefully)
    if start_cell in obstacle_cells:
        return None

    width = environment.width
    height = environment.height

    def h(cell: tuple[int, int]) -> float:
        """Euclidean heuristic to goal."""
        return math.sqrt((cell[0] - goal_cell[0]) ** 2 + (cell[1] - goal_cell[1]) ** 2)

    # Priority queue: (f_score, g_score, cell, first_step)
    # first_step is the neighbor of start_cell that begins this path
    open_heap: list[tuple[float, float, tuple[int, int], tuple[int, int]]] = []
    # came_first: cell -> first_step from start
    came_first: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start_cell: 0.0}

    for nx, ny, cost in _neighbors(start_cell, width, height):
        if (nx, ny) in blocked:
            continue
        if (nx, ny) == goal_cell:
            return Position(float(nx), float(ny))
        g = cost
        f = g + h((nx, ny))
        heapq.heappush(open_heap, (f, g, (nx, ny), (nx, ny)))
        if (nx, ny) not in g_score or g < g_score[(nx, ny)]:
            g_score[(nx, ny)] = g
            came_first[(nx, ny)] = (nx, ny)

    visited: set[tuple[int, int]] = {start_cell}

    while open_heap:
        f, g, current, first_step = heapq.heappop(open_heap)

        if current in visited:
            continue
        visited.add(current)

        if current == goal_cell:
            return Position(float(first_step[0]), float(first_step[1]))

        for nx, ny, cost in _neighbors(current, width, height):
            if (nx, ny) in visited:
                continue
            if (nx, ny) in blocked:
                continue
            new_g = g + cost
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
) -> list[tuple[int, int, float]]:
    """Return valid 8-connected neighbors with movement costs.

    Cardinal moves cost 1.0; diagonal moves cost sqrt(2).
    """
    cx, cy = cell
    candidates = [
        (cx + 1, cy,     1.0),
        (cx - 1, cy,     1.0),
        (cx,     cy + 1, 1.0),
        (cx,     cy - 1, 1.0),
        (cx + 1, cy + 1, math.sqrt(2)),
        (cx + 1, cy - 1, math.sqrt(2)),
        (cx - 1, cy + 1, math.sqrt(2)),
        (cx - 1, cy - 1, math.sqrt(2)),
    ]
    return [(nx, ny, cost) for nx, ny, cost in candidates if 0 <= nx < width and 0 <= ny < height]
