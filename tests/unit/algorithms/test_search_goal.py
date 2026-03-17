import dataclasses

from simulation.domain.robot_state import RobotId
from simulation.domain.environment import Environment
from simulation.primitives.position import Position
from simulation.domain.rescue_point import RescuePoint, RescuePointId
from simulation.domain.robot_state import RobotState
from simulation.algorithms.search_goal import compute_search_goal
from simulation.domain.task import TaskId, SpatialConstraint


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

def _rp(rp_id: int, x: int, y: int) -> RescuePoint:
    return RescuePoint(
        id=RescuePointId(rp_id),
        priority=5,
        spatial_constraint=SpatialConstraint(target=Position(x, y), max_distance=0),
        name=f"rp{rp_id}",
    )


def _state(x: int, y: int, waypoint: Position | None = None) -> RobotState:
    return RobotState(robot_id=RobotId(1), position=Position(x, y), current_waypoint=waypoint)


# ---------------------------------------------------------------------------
# Proximity lock
# ---------------------------------------------------------------------------

def test_proximity_lock_returns_rescue_point_when_within_threshold():
    rp = _rp(1, 3, 0)
    state = _state(0, 0)  # Manhattan distance to rp = 3
    env = Environment(width=10, height=10)

    goal = compute_search_goal(
        state=state,
        rescue_points={rp.id: rp},
        rescue_found={},
        proximity_threshold=5,
        pathfinding=_reachable,
        environment=env,
    )

    assert goal == Position(3, 0)


def test_proximity_lock_not_triggered_when_outside_threshold():
    rp = _rp(1, 9, 9)
    state = _state(0, 0)  # Manhattan distance = 18, well outside threshold=5
    env = Environment(width=10, height=10)

    goal = compute_search_goal(
        state=state,
        rescue_points={rp.id: rp},
        rescue_found={},
        proximity_threshold=5,
        pathfinding=_reachable,
        environment=env,
    )

    # No proximity lock — should fall through (no waypoint → picks new one)
    assert goal != Position(9, 9)


def test_proximity_lock_skips_already_found_rescue_points():
    rp = _rp(1, 1, 0)
    state = _state(0, 0)  # within any reasonable threshold
    env = Environment(width=10, height=10)

    goal = compute_search_goal(
        state=state,
        rescue_points={rp.id: rp},
        rescue_found={rp.id: True},
        proximity_threshold=10,
        pathfinding=_reachable,
        environment=env,
    )

    # Found point is skipped — should not lock onto it
    assert goal != rp.position


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
        rescue_found={},
        proximity_threshold=5,
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
        rescue_found={},
        proximity_threshold=0,
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
        rescue_found={},
        proximity_threshold=0,
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
        rescue_found={},
        proximity_threshold=0,
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
        rescue_found={},
        proximity_threshold=0,
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
        rescue_found={},
        proximity_threshold=0,
        pathfinding=_reachable,
        environment=env,
    )

    assert state.current_waypoint == state_before.current_waypoint
    assert state.position == state_before.position
