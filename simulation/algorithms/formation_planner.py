"""
Formation planner.

Pure functions for moving a formation one step toward a destination.
No task or robot domain knowledge — inputs are plain Positions and an Environment.

Two movement modes are available:

plan_formation_move (rigid):
    The entire formation (task + all eligible robots) shifts by the same
    (dx, dy). Fails if any formation cell lands on an obstacle.

plan_soft_formation_move (flexible):
    The task advances one step; each eligible robot independently moves to
    any valid cell within min_distance=1 of the new task position that is
    reachable in one step. Robots blocked in the rigid direction can step to
    the task's vacated cell or another adjacent cell instead of being locked
    in place by a single obstacle. Returns a per-robot old→new position map.
    Intended as a fallback when the rigid planner returns None.
"""

from __future__ import annotations

from collections.abc import Iterable

from simulation.algorithms.astar_pathfinding import astar_pathfind
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

    # Use A* on the task position to find the optimal next direction, including
    # routes that temporarily move away from the destination to go around obstacles.
    # Fall back to progress-only heuristic if A* finds no path.
    candidates: list[tuple[int, int]]
    if task_position is not None:
        astar_next = astar_pathfind(environment, task_position, destination)
        if astar_next is not None:
            primary = (astar_next.x - task_position.x, astar_next.y - task_position.y)
            fallbacks = sorted(
                [d for d in _DIRECTIONS if d != primary and _progress(d) > 0],
                key=_progress,
                reverse=True,
            )
            candidates = [primary] + fallbacks
        else:
            candidates = sorted(
                [d for d in _DIRECTIONS if _progress(d) > 0],
                key=_progress,
                reverse=True,
            )
    else:
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


def plan_soft_formation_move(
    task_position: Position,
    destination: Position,
    eligible_positions: list[Position],
    min_participants: int,
    environment: Environment,
    occupied: frozenset[Position],
) -> tuple[tuple[int, int], dict[Position, Position]] | None:
    """Flexible fallback when the rigid formation is blocked by an obstacle.

    Advances the task one step and lets each eligible robot independently
    move to any valid cell within Manhattan distance 1 of the new task
    position, reachable in one step from its current position.  A robot
    that cannot shift rigidly in the task's direction (e.g. because an
    obstacle sits there) can instead step to the task's vacated cell or
    another adjacent cell.

    Robots are assigned greedily, processing those with the fewest options
    first (min-conflicts heuristic) so that constrained robots claim their
    only valid cell before unconstrained ones.

    Args:
        task_position:     Current position of the task object.
        destination:       Where the task needs to reach.
        eligible_positions: Current positions of eligible robots (all within
                           min_distance of task_position this tick).
        min_participants:  Minimum number of robots that must be assignable
                           for the move to proceed.
        environment:       Grid environment (bounds + obstacles).
        occupied:          Positions occupied by non-formation robots.

    Returns:
        (direction, {old_pos: new_pos}) for participating robots, or None.
        Robots absent from the dict stay in place this tick and re-approach
        the task next tick.
    """
    current_dist = task_position.manhattan(destination)
    if current_dist == 0 or not eligible_positions:
        return None

    def _task_progress(direction: tuple[int, int]) -> int:
        dx, dy = direction
        return current_dist - Position(task_position.x + dx, task_position.y + dy).manhattan(destination)

    astar_next = astar_pathfind(environment, task_position, destination)
    if astar_next is not None:
        primary = (astar_next.x - task_position.x, astar_next.y - task_position.y)
        fallbacks = sorted(
            [d for d in _DIRECTIONS if d != primary and _task_progress(d) > 0],
            key=_task_progress,
            reverse=True,
        )
        candidates = [primary] + fallbacks
    else:
        candidates = sorted(
            [d for d in _DIRECTIONS if _task_progress(d) > 0],
            key=_task_progress,
            reverse=True,
        )

    for direction in candidates:
        dx, dy = direction
        new_task_pos = Position(task_position.x + dx, task_position.y + dy)

        if not environment.in_bounds(new_task_pos):
            continue
        if new_task_pos in environment.obstacles:
            continue
        if new_task_pos in occupied:
            continue

        # Cells within Manhattan 1 of new_task_pos that are valid to stand on.
        # Robots may also occupy the task cell itself (distance 0 ≤ min_distance).
        valid_adjacent: set[Position] = {new_task_pos}
        for adx, ady in _DIRECTIONS:
            cand = Position(new_task_pos.x + adx, new_task_pos.y + ady)
            if environment.in_bounds(cand) and cand not in environment.obstacles:
                valid_adjacent.add(cand)

        # For each robot, find the cells in valid_adjacent reachable in ≤1 step.
        robot_options: list[tuple[Position, list[Position]]] = []
        for robot_pos in eligible_positions:
            one_step: set[Position] = {robot_pos}  # staying is always an option
            for rdx, rdy in _DIRECTIONS:
                npos = Position(robot_pos.x + rdx, robot_pos.y + rdy)
                if (
                    environment.in_bounds(npos)
                    and npos not in environment.obstacles
                    and npos not in occupied
                ):
                    one_step.add(npos)
            options = sorted(
                [p for p in one_step if p in valid_adjacent],
                key=lambda p: (p.x, p.y),  # deterministic tiebreak
            )
            robot_options.append((robot_pos, options))

        # Greedy assignment: fewest-options robots first to minimise conflicts.
        robot_options.sort(key=lambda x: len(x[1]))

        assigned: dict[Position, Position] = {}
        used: set[Position] = set()
        for robot_pos, options in robot_options:
            for opt in options:
                if opt not in used:
                    assigned[robot_pos] = opt
                    used.add(opt)
                    break

        if len(assigned) >= min_participants:
            return direction, assigned

    return None
