import dataclasses
from unittest.mock import patch

from simulation.domain import RobotId, Environment, RescuePoint, RobotState, TaskId, SpatialConstraint
from simulation.primitives import Position
from simulation.algorithms import compute_search_goal


# ---------------------------------------------------------------------------
# Pathfinding stubs
# ---------------------------------------------------------------------------

def _reachable(env, start, goal):
    """Stub: waypoint is always reachable (returns an arbitrary next step)."""
    return Position(start.x + 1, start.y)


def _unreachable(env, start, goal):
    """Stub: waypoint is never reachable."""
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rp(rp_id: int, x: int, y: int, max_distance: int = 0) -> RescuePoint:
    return RescuePoint(
        id=TaskId(rp_id),
        priority=5,
        spatial_constraint=SpatialConstraint(target=Position(x, y), max_distance=max_distance),
        name=f"rp{rp_id}",
    )


def _state(x: int, y: int, waypoint: Position | None = None) -> RobotState:
    return RobotState(robot_id=RobotId(1), position=Position(x, y), current_waypoint=waypoint)


# ---------------------------------------------------------------------------
# Proximity lock
# ---------------------------------------------------------------------------

def test_proximity_lock_returns_none_when_within_threshold():
    # Within detection range: robot stops so discovery fires this tick
    # rather than continuing to walk onto the exact rescue point cell.
    rp = _rp(1, 3, 0, max_distance=5)
    state = _state(0, 0)  # Manhattan distance to rp = 3, within max_distance=5
    env = Environment(width=10, height=10)

    goal = compute_search_goal(
        state=state,
        rescue_points={rp.id: rp},
        rescue_found=frozenset(),
        pathfinding=_reachable,
        environment=env,
    )

    assert goal is None


def test_proximity_lock_not_triggered_when_outside_threshold():
    rp = _rp(1, 9, 9, max_distance=5)
    state = _state(0, 0)  # Manhattan distance = 18, well outside max_distance=5
    env = Environment(width=10, height=10)

    # Mock random fallback to return a fixed position that isn't (9, 9).
    with patch("simulation.algorithms.search_goal.random.randint", side_effect=[3, 3]):
        goal = compute_search_goal(
            state=state,
            rescue_points={rp.id: rp},
            rescue_found=frozenset(),
            pathfinding=_reachable,
            environment=env,
        )

    # No proximity lock — random fallback was chosen, not the rescue point
    assert goal != Position(9, 9)
    assert goal == Position(3, 3)


def test_proximity_lock_skips_already_found_rescue_points():
    rp = _rp(1, 1, 0, max_distance=10)
    state = _state(0, 0)  # within max_distance
    env = Environment(width=10, height=10)

    # Mock the random fallback to avoid flakily picking the rescue point position.
    with patch("simulation.algorithms.search_goal.random.randint", side_effect=[9, 9]):
        goal = compute_search_goal(
            state=state,
            rescue_points={rp.id: rp},
            rescue_found=frozenset({rp.id}),
            pathfinding=_reachable,
            environment=env,
        )

    # Found point is skipped — random fallback returned (9, 9) instead
    assert rp.spatial_constraint is not None
    assert goal != rp.spatial_constraint.target
    assert goal == Position(9, 9)


# ---------------------------------------------------------------------------
# Existing waypoint
# ---------------------------------------------------------------------------

def test_keeps_existing_reachable_waypoint():
    waypoint = Position(5, 5)
    state = _state(0, 0, waypoint=waypoint)
    env = Environment(width=10, height=10)

    goal = compute_search_goal(
        state=state,
        rescue_points={},
        rescue_found=frozenset(),
        pathfinding=_reachable,
        environment=env,
    )

    assert goal == waypoint


def test_clears_unreachable_waypoint_and_picks_new_random():
    # 2x1 env: robot at (0,0), only other cell is (1,0)
    state = _state(0, 0, waypoint=Position(5, 5))
    env = Environment(width=2, height=1)

    goal = compute_search_goal(
        state=state,
        rescue_points={},
        rescue_found=frozenset(),
        pathfinding=_unreachable,
        environment=env,
    )

    # Waypoint was unreachable — should pick the only other walkable cell
    assert goal == Position(1, 0)


def test_robot_at_waypoint_falls_through_to_new_random():
    # Robot is already AT its waypoint → condition is False → picks new one
    # 2x1 env: robot at (0,0), only other cell is (1,0)
    state = _state(0, 0, waypoint=Position(0, 0))
    env = Environment(width=2, height=1)

    goal = compute_search_goal(
        state=state,
        rescue_points={},
        rescue_found=frozenset(),
        pathfinding=_reachable,
        environment=env,
    )

    assert goal == Position(1, 0)


# ---------------------------------------------------------------------------
# No waypoint — picks random
# ---------------------------------------------------------------------------

def test_picks_random_walkable_cell_when_no_waypoint():
    # 2x1 env: robot at (0,0), only other cell is (1,0)
    state = _state(0, 0, waypoint=None)
    env = Environment(width=2, height=1)

    goal = compute_search_goal(
        state=state,
        rescue_points={},
        rescue_found=frozenset(),
        pathfinding=_reachable,
        environment=env,
    )

    assert goal == Position(1, 0)


# ---------------------------------------------------------------------------
# No walkable cell
# ---------------------------------------------------------------------------

def test_returns_none_when_no_walkable_cell_exists():
    # 1x1 env: robot is the only cell — no valid random target
    state = _state(0, 0, waypoint=None)
    env = Environment(width=1, height=1)

    goal = compute_search_goal(
        state=state,
        rescue_points={},
        rescue_found=frozenset(),
        pathfinding=_unreachable,
        environment=env,
    )

    assert goal is None


# ---------------------------------------------------------------------------
# No mutation
# ---------------------------------------------------------------------------

def test_does_not_mutate_input_state():
    waypoint = Position(5, 5)
    state = _state(0, 0, waypoint=waypoint)
    state_before = dataclasses.replace(state)
    env = Environment(width=10, height=10)

    compute_search_goal(
        state=state,
        rescue_points={},
        rescue_found=frozenset(),
        pathfinding=_reachable,
        environment=env,
    )

    assert state.current_waypoint == state_before.current_waypoint
    assert state.position == state_before.position
