"""
Unit tests for astar_pathfind.

Covers:
- Already at goal → returns goal (not None)
- Start on obstacle → None
- Unreachable goal (enclosed by obstacles) → None
- Adjacent goal → returns goal directly (fast path)
- Path around obstacle → correct first step direction
- Goal is an obstacle cell → still pathfinds there
- Out-of-bounds goal → None
- 1-wide corridor → can navigate through
- Returned step is always cardinal (Manhattan distance == 1 from start)
- Determinism: same inputs always produce same output
"""

from __future__ import annotations

from simulation.algorithms import astar_pathfind
from simulation.domain import Environment
from simulation.primitives import Position


def test_returns_goal_when_already_at_goal():
    # Arrange: open grid, start and goal are the same cell
    env = Environment(5, 5)
    start = Position(2, 2)
    goal = Position(2, 2)

    # Act
    result = astar_pathfind(env, start, goal)

    # Assert: returns goal directly (not None — robot is already there)
    assert result == goal


def test_returns_none_when_start_on_obstacle():
    # Arrange: robot's own cell is an obstacle (degenerate state)
    env = Environment(5, 5)
    start = Position(0, 0)
    env.add_obstacle(start)
    goal = Position(4, 4)

    # Act
    result = astar_pathfind(env, start, goal)

    # Assert: no path can begin from an obstacle cell
    assert result is None


def test_returns_none_when_goal_unreachable():
    # Arrange: goal at (2,2) sealed off by obstacles on all four cardinal sides
    env = Environment(5, 5)
    goal = Position(2, 2)
    for pos in [Position(1, 2), Position(3, 2), Position(2, 1), Position(2, 3)]:
        env.add_obstacle(pos)
    start = Position(0, 0)

    # Act
    result = astar_pathfind(env, start, goal)

    # Assert: open heap drains with goal never reached
    assert result is None


def test_returns_goal_when_adjacent():
    # Arrange: goal is exactly one step east of start (exercises the fast path
    #          in the initial-neighbour loop that skips full A* search)
    env = Environment(5, 5)
    start = Position(0, 0)
    goal = Position(1, 0)

    # Act
    result = astar_pathfind(env, start, goal)

    # Assert: fast path returns goal immediately without expanding further
    assert result == goal


def test_routes_around_obstacle():
    # Arrange: row y=0 fully blocked; x=1-3 on y=1 also blocked.
    #   Only viable path detours through y=2.
    #
    #   Grid (5 x 3):
    #     x: 0 1 2 3 4
    #   y=0: # # # # #   ← all obstacles
    #   y=1: S # # # G   ← start=(0,1), wall at x=1-3, goal=(4,1)
    #   y=2: . . . . .   ← open; only viable detour route
    #
    #   Path: (0,1)→(0,2)→(1,2)→(2,2)→(3,2)→(4,2)→(4,1)
    #   So the only valid first step is south: Position(0, 2)
    env = Environment(5, 3)
    for x in range(5):
        env.add_obstacle(Position(x, 0))    # block entire top row
    for x in range(1, 4):
        env.add_obstacle(Position(x, 1))    # block direct east path
    start = Position(0, 1)
    goal = Position(4, 1)

    # Act
    result = astar_pathfind(env, start, goal)

    # Assert: only valid first step is south into the open detour row
    assert result == Position(0, 2)


def test_pathfinds_to_goal_on_obstacle():
    # Arrange: the goal cell is itself an obstacle.
    #   The implementation explicitly allows pathfinding to an obstacle goal
    #   (lines that skip obstacle cells make an exception when the cell == goal).
    env = Environment(5, 5)
    goal = Position(4, 4)
    env.add_obstacle(goal)
    start = Position(0, 0)

    # Act
    result = astar_pathfind(env, start, goal)

    # Assert: a first step is returned — goal is reachable even on an obstacle
    assert result is not None
    assert result != start  # robot actually moved toward goal


def test_returns_none_for_out_of_bounds_goal():
    # Arrange: goal lies outside the 5×5 grid entirely
    env = Environment(5, 5)
    start = Position(0, 0)
    goal = Position(10, 10)

    # Act
    result = astar_pathfind(env, start, goal)

    # Assert: _neighbors never generates out-of-bounds cells so goal is never found
    assert result is None


def test_navigates_one_wide_corridor():
    # Arrange: rows y=0 and y=2 are fully blocked, leaving a single-cell-wide
    #   east corridor at y=1.
    #
    #   Grid (5 x 3):
    #     x: 0 1 2 3 4
    #   y=0: # # # # #
    #   y=1: S . . . G   ← only path
    #   y=2: # # # # #
    env = Environment(5, 3)
    for x in range(5):
        env.add_obstacle(Position(x, 0))
        env.add_obstacle(Position(x, 2))
    start = Position(0, 1)
    goal = Position(4, 1)

    # Act
    result = astar_pathfind(env, start, goal)

    # Assert: robot takes the only available step, east along the corridor
    assert result == Position(1, 1)


def test_step_is_cardinal_distance_one_from_start():
    # Arrange: open 10×10 grid with a long diagonal journey
    env = Environment(10, 10)
    start = Position(0, 0)
    goal = Position(9, 9)

    # Act
    result = astar_pathfind(env, start, goal)

    # Assert: returned cell is always an adjacent cardinal neighbour (no diagonals,
    #   no teleportation) — Manhattan distance from start must be exactly 1
    assert result is not None
    manhattan = abs(result.x - start.x) + abs(result.y - start.y)
    assert manhattan == 1


def test_deterministic_same_inputs_same_output():
    # Arrange: grid with a partial vertical wall that forces a detour
    env = Environment(10, 10)
    for y in range(5):
        env.add_obstacle(Position(5, y))    # wall on left half only
    start = Position(0, 0)
    goal = Position(9, 9)

    # Act: call twice with identical inputs
    result1 = astar_pathfind(env, start, goal)
    result2 = astar_pathfind(env, start, goal)

    # Assert: heap ordering is deterministic — same first step every time
    assert result1 is not None
    assert result1 == result2
