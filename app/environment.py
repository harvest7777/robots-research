"""
app/environment.py

40×30 disaster-response environment.

Districts
---------
  NW corner  : RESTRICTED zone   (collapsed bunker)
  N center   : INSPECTION zone   (command post)
  NE corner  : CHARGING zone     (robot depot)
  SW corner  : LOADING zone      (extraction staging)
  SE corner  : MAINTENANCE zone  (field medical bay)
  Center     : RESTRICTED zone   (collapsed structure — dense rubble)

Layout
------
  Two vertical dividers (x=13, x=27) split the map into
  West / Center / East districts.

  Two horizontal barriers (y=11, y=20) subdivide each district
  into three tiers (North, Mid, South), with narrow corridors
  forcing interesting routing and formation contention.

  A southern wall at y=23 separates the extraction staging area
  from the main map; robots access it through the loading-zone
  gap (x≤6) or the maintenance gap (x=32–33).

Five casualties are scattered across all three districts and both
tiers.  Each spawns a MoveTask when discovered, carrying the victim
to a safe extraction point.
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
from simulation.primitives import Capability, Position, Zone, ZoneId, ZoneType

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
    o: list[Position] = []

    # ── NORTH BAND (y=5) ─────────────────────────────────────────────
    # Separates the top zone-strip (RESTRICTED / INSPECTION / CHARGING)
    # from the main map.  Gaps: x 0-4 (bunker passage), x 14-15
    # (inspection entry west), x 25-26 (inspection exit east),
    # x 35-39 (charging passage).
    o += _rect(5, 5, 13, 5)
    o += _rect(16, 5, 24, 5)
    o += _rect(27, 5, 34, 5)

    # ── SOUTH BAND (y=23) ────────────────────────────────────────────
    # Seals the southern staging area.  Gaps: x 0-6 (loading zone
    # passage) and x 32-33 (maintenance entry).
    o += _rect(7, 23, 31, 23)
    o += _rect(34, 23, 39, 23)

    # ── VERTICAL DISTRICT DIVIDERS ───────────────────────────────────
    # Left divider (x=13): west ↔ center.
    # Corridors at y=12 (upper) and y=19 (lower).
    o += _rect(13, 6, 13, 11)
    o += _rect(13, 13, 13, 18)
    o += _rect(13, 20, 13, 22)

    # Right divider (x=27): center ↔ east.
    o += _rect(27, 6, 27, 11)
    o += _rect(27, 13, 27, 18)
    o += _rect(27, 20, 27, 22)

    # ── HORIZONTAL MID BARRIERS ──────────────────────────────────────
    # Upper barrier (y=11): one gap per district.
    # West gap at x=7; center gap at x=19-20; east gap at x=33.
    o += _rect(1, 11, 6, 11)
    o += _rect(8, 11, 12, 11)
    o += _rect(14, 11, 18, 11)
    o += _rect(21, 11, 26, 11)
    o += _rect(28, 11, 32, 11)
    o += _rect(34, 11, 38, 11)

    # Lower barrier (y=20): shifted gaps for asymmetry.
    # West gap at x=5; center gap at x=20; east gap at x=31.
    o += _rect(1, 20, 4, 20)
    o += _rect(6, 20, 12, 20)
    o += _rect(14, 20, 19, 20)
    o += _rect(21, 20, 26, 20)
    o += _rect(28, 20, 30, 20)
    o += _rect(32, 20, 38, 20)

    # ── CENTRAL CORRIDOR MAZE (x 14-26, y 12-19) ─────────────────────
    # Dense but navigable rubble inside the RESTRICTED center zone.
    o += _rect(15, 12, 16, 13)   # NW clump
    o += _rect(22, 12, 24, 13)   # NE clump
    o += _rect(14, 15, 15, 16)   # W mid block
    o += _rect(18, 13, 20, 14)   # center-north rubble
    o += _rect(22, 15, 24, 16)   # E mid block
    o += _rect(15, 17, 17, 18)   # SW footing
    o += _rect(21, 17, 23, 18)   # SE footing
    o += _rect(18, 16, 20, 17)   # center-south rubble
    o += _rect(25, 14, 26, 15)   # east corridor pinch

    # ── WEST DISTRICT INTERIOR ───────────────────────────────────────
    o += _rect(1, 7, 3, 8)       # NW clutter
    o += _rect(10, 7, 11, 9)     # NE clutter
    o += _rect(5, 9, 8, 9)       # mid-north scatter
    o += _rect(1, 14, 3, 15)     # mid-west block
    o += _rect(8, 13, 10, 14)    # mid-east block
    o += _rect(3, 17, 5, 18)     # lower-west clutter
    o += _rect(9, 17, 11, 18)    # lower-east clutter
    o += _rect(2, 21, 5, 22)     # near south wall

    # ── EAST DISTRICT INTERIOR ───────────────────────────────────────
    o += _rect(29, 7, 32, 8)     # NW clutter (east)
    o += _rect(36, 7, 38, 9)     # NE clutter (east)
    o += _rect(30, 9, 34, 9)     # mid-north scatter
    o += _rect(28, 14, 30, 15)   # mid-west block (east)
    o += _rect(35, 13, 37, 14)   # mid-east block (east)
    o += _rect(29, 17, 31, 18)   # lower-west clutter (east)
    o += _rect(36, 17, 38, 18)   # lower-east clutter (east)
    o += _rect(34, 21, 38, 22)   # near south wall (east)

    # ── SOUTHERN STAGING SCATTER ─────────────────────────────────────
    o += _rect(8, 25, 10, 26)
    o += _rect(14, 24, 16, 25)
    o += _rect(17, 27, 19, 28)
    o += _rect(22, 25, 24, 26)
    o += _rect(27, 26, 29, 27)
    o += _rect(31, 24, 32, 25)

    # ── ADDITIONAL NORTH-TIER SCATTER ────────────────────────────────
    o += _rect(1, 6, 2, 7)       # extreme NW scatter
    o += _rect(11, 6, 12, 7)     # west north scatter
    o += _rect(28, 6, 29, 7)     # east north scatter
    o += _rect(37, 6, 38, 7)     # extreme NE scatter

    # ── PROTECT KEY TARGETS ──────────────────────────────────────────
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

    # ── ZONES ────────────────────────────────────────────────────────
    def _zone(zid: int, ztype: ZoneType, x0: int, y0: int, x1: int, y1: int) -> Zone:
        return Zone.from_positions(
            id=ZoneId(zid),
            zone_type=ztype,
            positions=frozenset(_rect(x0, y0, x1, y1)),
        )

    env.add_zone(_zone(1, ZoneType.RESTRICTED,   0,  0,  4,  4))  # NW bunker
    env.add_zone(_zone(2, ZoneType.CHARGING,    35,  0, 39,  4))  # NE charging depot
    env.add_zone(_zone(3, ZoneType.INSPECTION,  15,  0, 25,  4))  # N command post
    env.add_zone(_zone(4, ZoneType.LOADING,      0, 24,  6, 29))  # SW extraction staging
    env.add_zone(_zone(5, ZoneType.MAINTENANCE, 33, 23, 39, 29))  # SE field medical bay
    env.add_zone(_zone(6, ZoneType.RESTRICTED,  17, 12, 23, 17))  # central collapsed structure

    # ── RESCUE POINTS (all spawn MoveTasks) ──────────────────────────
    def _rescue_point(
        rp_id: TaskId,
        name: str,
        casualty_pos: Position,
        move_task_id: TaskId,
        extraction_pos: Position,
        min_robots: int = 2,
    ) -> RescuePoint:
        move_task = MoveTask(
            id=move_task_id,
            priority=9,
            destination=extraction_pos,
            min_robots_required=min_robots,
            min_distance=1,
            required_capabilities=frozenset({Capability.VISION}),
        )
        return RescuePoint(
            id=rp_id,
            name=name,
            spatial_constraint=SpatialConstraint(target=casualty_pos, max_distance=1),
            task=move_task,
            initial_task_state=MoveTaskState(
                task_id=move_task_id,
                current_position=casualty_pos,
            ),
        )

    env.add_rescue_point(
        _rescue_point(
            RESCUE_POINT_ALPHA_ID,
            "Casualty Alpha",
            CASUALTY_ALPHA,
            MOVE_TASK_ALPHA_ID,
            EXTRACTION_ALPHA,
        )
    )
    env.add_rescue_point(
        _rescue_point(
            RESCUE_POINT_BRAVO_ID,
            "Casualty Bravo",
            CASUALTY_BRAVO,
            MOVE_TASK_BRAVO_ID,
            EXTRACTION_BRAVO,
        )
    )
    env.add_rescue_point(
        _rescue_point(
            RESCUE_POINT_CHARLIE_ID,
            "Casualty Charlie",
            CASUALTY_CHARLIE,
            MOVE_TASK_CHARLIE_ID,
            EXTRACTION_CHARLIE,
        )
    )
    env.add_rescue_point(
        _rescue_point(
            RESCUE_POINT_DELTA_ID,
            "Casualty Delta",
            CASUALTY_DELTA,
            MOVE_TASK_DELTA_ID,
            EXTRACTION_DELTA,
        )
    )
    env.add_rescue_point(
        _rescue_point(
            RESCUE_POINT_ECHO_ID,
            "Casualty Echo",
            CASUALTY_ECHO,
            MOVE_TASK_ECHO_ID,
            EXTRACTION_ECHO,
            min_robots=3,  # hardest rescue — needs a larger formation
        )
    )

    return env
