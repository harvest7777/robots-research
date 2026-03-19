"""
Unit tests for formation_planner.

Each test exercises one behaviour of plan_formation_move in isolation.
"""

from __future__ import annotations

from simulation.domain import Environment
from simulation.primitives import Position
from simulation.algorithms import plan_formation_move


def _env(width: int = 10, height: int = 10) -> Environment:
    return Environment(width=width, height=height)


# ---------------------------------------------------------------------------
# Basic movement
# ---------------------------------------------------------------------------

def test_moves_toward_destination_when_clear():
    formation = frozenset({Position(3, 3)})
    result = plan_formation_move(formation, Position(6, 3), _env(), frozenset())
    assert result == (1, 0)


def test_moves_vertically_when_x_aligned():
    formation = frozenset({Position(3, 3)})
    result = plan_formation_move(formation, Position(3, 7), _env(), frozenset())
    assert result == (0, 1)


def test_already_at_destination_returns_none():
    formation = frozenset({Position(5, 5)})
    result = plan_formation_move(formation, Position(5, 5), _env(), frozenset())
    assert result is None


def test_empty_formation_returns_none():
    result = plan_formation_move(frozenset(), Position(5, 5), _env(), frozenset())
    assert result is None


# ---------------------------------------------------------------------------
# Multi-position formation moves as a unit
# ---------------------------------------------------------------------------

def test_plus_formation_moves_right():
    # + shape centered at (3, 3)
    formation = frozenset({
        Position(3, 3),
        Position(2, 3), Position(4, 3),
        Position(3, 2), Position(3, 4),
    })
    result = plan_formation_move(formation, Position(8, 3), _env(), frozenset())
    assert result == (1, 0)


# ---------------------------------------------------------------------------
# Obstacle avoidance
# ---------------------------------------------------------------------------

def test_blocked_by_obstacle_returns_none():
    env = _env()
    env.add_obstacle(Position(4, 3))  # directly in path
    formation = frozenset({Position(3, 3)})
    # destination is to the right but only direction available is right
    result = plan_formation_move(formation, Position(6, 3), env, frozenset())
    assert result is None


def test_detours_around_obstacle():
    env = _env()
    env.add_obstacle(Position(4, 3))
    # destination is down-right — vertical move is still valid
    formation = frozenset({Position(3, 3)})
    result = plan_formation_move(formation, Position(4, 6), env, frozenset())
    assert result == (0, 1)


def test_out_of_bounds_blocks_direction():
    env = Environment(width=5, height=5)
    formation = frozenset({Position(4, 2)})  # at right edge
    result = plan_formation_move(formation, Position(4, 2), env, frozenset())
    assert result is None  # already at destination


def test_formation_at_edge_cannot_move_out_of_bounds():
    env = Environment(width=5, height=5)
    formation = frozenset({Position(4, 2)})  # right edge
    # destination further right — only valid direction would go OOB
    result = plan_formation_move(formation, Position(10, 2), env, frozenset())
    assert result is None


# ---------------------------------------------------------------------------
# Occupied (other robots) avoidance
# ---------------------------------------------------------------------------

def test_blocked_by_occupied_robot():
    formation = frozenset({Position(3, 3)})
    occupied = frozenset({Position(4, 3)})
    result = plan_formation_move(formation, Position(6, 3), _env(), occupied)
    assert result is None


def test_detours_around_occupied_robot():
    formation = frozenset({Position(3, 3)})
    occupied = frozenset({Position(4, 3)})
    # destination is down-right — vertical step is free
    result = plan_formation_move(formation, Position(4, 6), _env(), occupied)
    assert result == (0, 1)


def test_multi_position_formation_blocked_if_any_member_hits_occupied():
    # formation spans (3,3) and (4,3); shifting right puts (5,3) which is occupied
    formation = frozenset({Position(3, 3), Position(4, 3)})
    occupied = frozenset({Position(5, 3)})
    result = plan_formation_move(formation, Position(8, 3), _env(), occupied)
    assert result is None
