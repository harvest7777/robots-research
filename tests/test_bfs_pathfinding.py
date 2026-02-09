"""Tests for BFS pathfinding algorithm."""

from __future__ import annotations

from simulation_models.environment import Environment
from simulation_models.position import Position
from pathfinding_algorithms import bfs_pathfind


def _make_env(width: int = 5, height: int = 5) -> Environment:
    """Create a simple empty environment."""
    return Environment(width=width, height=height)


class TestBfsPathfinding:
    def test_start_equals_goal_returns_start(self) -> None:
        env = _make_env()
        pos = Position(2, 2)
        result = bfs_pathfind(env, pos, pos, frozenset())
        assert result == pos

    def test_adjacent_goal_returns_goal(self) -> None:
        env = _make_env()
        start = Position(2, 2)
        goal = Position(3, 2)  # right neighbor
        result = bfs_pathfind(env, start, goal, frozenset())
        assert result == goal

    def test_straight_line_path_returns_correct_first_step(self) -> None:
        env = _make_env()
        start = Position(0, 0)
        goal = Position(3, 0)  # 3 steps right
        result = bfs_pathfind(env, start, goal, frozenset())
        assert result == Position(1, 0)

    def test_path_around_obstacle(self) -> None:
        env = _make_env()
        # Block direct path with obstacle
        env.add_obstacle(Position(1, 0))
        start = Position(0, 0)
        goal = Position(2, 0)
        result = bfs_pathfind(env, start, goal, frozenset())
        # Must go down first to get around the obstacle
        assert result == Position(0, 1)

    def test_path_around_occupied_position(self) -> None:
        env = _make_env()
        start = Position(0, 0)
        goal = Position(2, 0)
        occupied = frozenset({Position(1, 0)})
        result = bfs_pathfind(env, start, goal, occupied)
        # Must go down to get around occupied cell
        assert result == Position(0, 1)

    def test_unreachable_goal_returns_none(self) -> None:
        env = _make_env(3, 3)
        # Wall off the goal completely
        goal = Position(2, 2)
        env.add_obstacle(Position(1, 2))
        env.add_obstacle(Position(2, 1))
        result = bfs_pathfind(env, Position(0, 0), goal, frozenset())
        assert result is None

    def test_surrounded_start_returns_none(self) -> None:
        env = _make_env()
        start = Position(2, 2)
        goal = Position(4, 4)
        # Block all 4 neighbors of start
        occupied = frozenset({
            Position(2, 1),
            Position(2, 3),
            Position(1, 2),
            Position(3, 2),
        })
        result = bfs_pathfind(env, start, goal, occupied)
        assert result is None

    def test_full_path_stays_in_bounds(self) -> None:
        """Walk the full path from start to goal, verifying every step is in bounds."""
        env = _make_env(5, 5)
        env.add_obstacle(Position(2, 0))
        env.add_obstacle(Position(2, 1))
        env.add_obstacle(Position(2, 2))
        start = Position(0, 0)
        goal = Position(4, 0)

        current = start
        steps = 0
        max_steps = 50  # safety limit
        while current != goal and steps < max_steps:
            next_pos = bfs_pathfind(env, current, goal, frozenset())
            assert next_pos is not None, f"Got stuck at {current}"
            assert env.in_bounds(next_pos), f"Step {next_pos} is out of bounds"
            assert next_pos not in env.obstacles, f"Step {next_pos} is an obstacle"
            current = next_pos
            steps += 1

        assert current == goal, f"Did not reach goal after {steps} steps"

    def test_corner_start(self) -> None:
        env = _make_env(3, 3)
        start = Position(0, 0)
        goal = Position(2, 2)
        result = bfs_pathfind(env, start, goal, frozenset())
        assert result in (Position(1, 0), Position(0, 1))

    def test_goal_is_obstacle_unreachable(self) -> None:
        """Goal on an obstacle cell is unreachable (BFS never matches it)."""
        env = _make_env(3, 3)
        env.add_obstacle(Position(2, 2))
        result = bfs_pathfind(env, Position(0, 0), Position(2, 2), frozenset())
        assert result is None
