"""
Search Goal

Pure function for computing the movement goal of a SEARCH robot each tick.
Returns a single Position (or None) — the caller is responsible for writing
it back to state.current_waypoint. No state is mutated here.
"""

from __future__ import annotations

import random

_MAX_RANDOM_GOAL_ATTEMPTS = 1000
"""Max attempts to find a random walkable cell before giving up."""

from simulation.domain.environment import Environment
from simulation.algorithms.movement_planner import PathfindingAlgorithm
from simulation.primitives.position import Position
from simulation.domain.base_task import TaskId
from simulation.domain.rescue_point import RescuePoint
from simulation.domain.robot_state import RobotState


def compute_search_goal(
    state: RobotState,
    rescue_points: dict[TaskId, RescuePoint],
    rescue_found: dict[TaskId, bool],
    pathfinding: PathfindingAlgorithm,
    environment: Environment,
) -> Position | None:
    """Compute the roaming goal for a SEARCH robot.

    Priority order:
    1. Proximity lock: if any unfound rescue point is within Manhattan distance
       <= its spatial_constraint.max_distance, lock the robot onto that rescue point.
    2. Keep current waypoint: if one is set, not yet reached, and still
       reachable via pathfinding.
    3. Random walkable cell: pick a new random non-obstacle position.

    Returns:
        The goal Position, or None if no valid goal exists. The caller must
        write the returned value to state.current_waypoint. This function
        does not mutate state.
    """
    # Step 1: Proximity lock onto any nearby unfound rescue point
    for rp in rescue_points.values():
        if rescue_found.get(rp.id):
            continue
        assert rp.spatial_constraint is not None
        rp_position = rp.spatial_constraint.target
        if state.position.manhattan(rp_position) <= rp.spatial_constraint.max_distance:
            return rp_position

    # Step 2: Keep existing waypoint if reachable and not yet reached
    if state.current_waypoint is not None and state.current_waypoint != state.position:
        next_step = pathfinding(environment, state.position, state.current_waypoint)
        if next_step is not None:
            return state.current_waypoint
        # Waypoint unreachable — fall through to pick a new one

    # Step 3: Pick a random walkable position
    for _ in range(_MAX_RANDOM_GOAL_ATTEMPTS):
        x = random.randint(0, environment.width - 1)
        y = random.randint(0, environment.height - 1)
        pos = Position(x, y)
        if pos not in environment.obstacles and pos != state.position:
            return pos

    return None
