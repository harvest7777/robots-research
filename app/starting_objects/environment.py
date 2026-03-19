"""
app/environment.py

40×30 disaster-response environment.

Five casualties are scattered across the map; each spawns a MoveTask
when discovered, carrying the victim to a safe extraction point.

Obstacles are sparse rubble clusters that create routing variation
without forming bottlenecks that would block multi-robot formations.
"""

from __future__ import annotations

from simulation.domain import (
    Environment,
    MoveTask,
    MoveTaskState,
    RescuePoint,
    SpatialConstraint,
    TaskId,
)
from simulation.primitives import Capability, Position

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

WIDTH = 40
HEIGHT = 30

# ---------------------------------------------------------------------------
# Task IDs
# ---------------------------------------------------------------------------

RESCUE_POINT_ALPHA_ID = TaskId(10)
RESCUE_POINT_BRAVO_ID = TaskId(11)
RESCUE_POINT_CHARLIE_ID = TaskId(12)
RESCUE_POINT_DELTA_ID = TaskId(13)
RESCUE_POINT_ECHO_ID = TaskId(14)

MOVE_TASK_ALPHA_ID = TaskId(20)
MOVE_TASK_BRAVO_ID = TaskId(21)
MOVE_TASK_CHARLIE_ID = TaskId(22)
MOVE_TASK_DELTA_ID = TaskId(23)
MOVE_TASK_ECHO_ID = TaskId(24)

# ---------------------------------------------------------------------------
# Key positions
# ---------------------------------------------------------------------------

# Casualties: where each victim is found.
CASUALTY_ALPHA = Position(7, 8)     # west district, north tier
CASUALTY_BRAVO = Position(31, 6)    # east district, north tier
CASUALTY_CHARLIE = Position(9, 16)  # west district, mid tier
CASUALTY_DELTA = Position(33, 16)   # east district, mid tier
CASUALTY_ECHO = Position(20, 25)    # south staging area — hardest to reach

# Extraction destinations for each MoveTask.
EXTRACTION_ALPHA = Position(3, 26)   # inside LOADING zone
EXTRACTION_BRAVO = Position(37, 3)   # inside CHARGING zone
EXTRACTION_CHARLIE = Position(1, 14) # west corridor open ground
EXTRACTION_DELTA = Position(36, 26)  # inside MAINTENANCE zone
EXTRACTION_ECHO = Position(12, 28)   # south open area

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rect(x0: int, y0: int, x1: int, y1: int) -> list[Position]:
    """Inclusive axis-aligned rectangle of positions."""
    return [Position(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]


# ---------------------------------------------------------------------------
# Obstacle construction
# ---------------------------------------------------------------------------

_PROTECTED: frozenset[Position] = frozenset(
    {
        CASUALTY_ALPHA,
        CASUALTY_BRAVO,
        CASUALTY_CHARLIE,
        CASUALTY_DELTA,
        CASUALTY_ECHO,
        EXTRACTION_ALPHA,
        EXTRACTION_BRAVO,
        EXTRACTION_CHARLIE,
        EXTRACTION_DELTA,
        EXTRACTION_ECHO,
    }
)


def _build_obstacles() -> list[Position]:
    # Sparse rubble clusters — create routing variation without bottlenecks.
    # No walls or corridors; formations can navigate freely around any cluster.
    o: list[Position] = []

    o += _rect(17, 6, 20, 8)    # centre-north rubble
    o += _rect(5, 12, 7, 14)    # west-mid rubble
    o += _rect(24, 12, 26, 14)  # east-mid rubble
    o += _rect(16, 19, 18, 21)  # centre-south rubble
    o += _rect(30, 18, 32, 20)  # east-south rubble

    blocked = {p for p in o if 0 <= p.x < WIDTH and 0 <= p.y < HEIGHT}
    blocked -= _PROTECTED
    return sorted(blocked, key=lambda p: (p.y, p.x))


_OBSTACLES: list[Position] = _build_obstacles()


# ---------------------------------------------------------------------------
# Environment builder
# ---------------------------------------------------------------------------


def build_environment() -> Environment:
    """Return a fully configured 40×30 Environment."""
    env = Environment(width=WIDTH, height=HEIGHT)

    for pos in _OBSTACLES:
        env.add_obstacle(pos)

    env.add_rescue_point(RescuePoint(
        id=RESCUE_POINT_ALPHA_ID,
        name="Casualty Alpha",
        spatial_constraint=SpatialConstraint(target=CASUALTY_ALPHA, max_distance=1),
        task=MoveTask(
            id=MOVE_TASK_ALPHA_ID, priority=9, destination=EXTRACTION_ALPHA,
            min_robots_required=2, min_distance=1,
            required_capabilities=frozenset({Capability.VISION}),
        ),
        initial_task_state=MoveTaskState(task_id=MOVE_TASK_ALPHA_ID, current_position=CASUALTY_ALPHA),
    ))
    env.add_rescue_point(RescuePoint(
        id=RESCUE_POINT_BRAVO_ID,
        name="Casualty Bravo",
        spatial_constraint=SpatialConstraint(target=CASUALTY_BRAVO, max_distance=1),
        task=MoveTask(
            id=MOVE_TASK_BRAVO_ID, priority=9, destination=EXTRACTION_BRAVO,
            min_robots_required=2, min_distance=1,
            required_capabilities=frozenset({Capability.VISION}),
        ),
        initial_task_state=MoveTaskState(task_id=MOVE_TASK_BRAVO_ID, current_position=CASUALTY_BRAVO),
    ))
    env.add_rescue_point(RescuePoint(
        id=RESCUE_POINT_CHARLIE_ID,
        name="Casualty Charlie",
        spatial_constraint=SpatialConstraint(target=CASUALTY_CHARLIE, max_distance=1),
        task=MoveTask(
            id=MOVE_TASK_CHARLIE_ID, priority=9, destination=EXTRACTION_CHARLIE,
            min_robots_required=2, min_distance=1,
            required_capabilities=frozenset({Capability.VISION}),
        ),
        initial_task_state=MoveTaskState(task_id=MOVE_TASK_CHARLIE_ID, current_position=CASUALTY_CHARLIE),
    ))
    env.add_rescue_point(RescuePoint(
        id=RESCUE_POINT_DELTA_ID,
        name="Casualty Delta",
        spatial_constraint=SpatialConstraint(target=CASUALTY_DELTA, max_distance=1),
        task=MoveTask(
            id=MOVE_TASK_DELTA_ID, priority=9, destination=EXTRACTION_DELTA,
            min_robots_required=2, min_distance=1,
            required_capabilities=frozenset({Capability.VISION}),
        ),
        initial_task_state=MoveTaskState(task_id=MOVE_TASK_DELTA_ID, current_position=CASUALTY_DELTA),
    ))
    env.add_rescue_point(RescuePoint(
        id=RESCUE_POINT_ECHO_ID,
        name="Casualty Echo",
        spatial_constraint=SpatialConstraint(target=CASUALTY_ECHO, max_distance=1),
        task=MoveTask(
            id=MOVE_TASK_ECHO_ID, priority=9, destination=EXTRACTION_ECHO,
            min_robots_required=3, min_distance=1,
            required_capabilities=frozenset({Capability.VISION}),
        ),
        initial_task_state=MoveTaskState(task_id=MOVE_TASK_ECHO_ID, current_position=CASUALTY_ECHO),
    ))

    return env
