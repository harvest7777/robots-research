"""
app/robots.py

Seven robots initialised for the 40×30 disaster-response environment.

Placement rationale
-------------------
  R1  Central Scout   — starts inside the INSPECTION zone (command post).
                        Good sightlines into all three districts.
  R2  West Scout      — starts in the west north tier, close to Casualty Alpha.
  R3  West Carrier A  — west north tier, ready to form a carry team once Alpha
                        is found.
  R4  West Carrier B  — west mid tier, covers Casualty Charlie territory.
  R5  East Carrier A  — east north tier, near Casualty Bravo.
  R6  East Specialist — east mid tier near Casualty Delta; REPAIR capability
                        adds flexibility for future maintenance tasks.
  R7  South Heavy     — pre-positioned in the south staging area so it can
                        join the Echo formation quickly (Echo needs 3 robots).

Capability breakdown
--------------------
  Scouts (R1, R2)     : VISION + SENSING
  Carriers (R3-R5, R7): VISION + MANIPULATION
  Specialist (R6)     : VISION + MANIPULATION + REPAIR
"""

from __future__ import annotations

from simulation.domain import Robot, RobotState
from simulation.domain.robot_state import RobotId
from simulation.primitives import Capability, Position

# ---------------------------------------------------------------------------
# Robot IDs
# ---------------------------------------------------------------------------

R1 = RobotId(1)
R2 = RobotId(2)
R3 = RobotId(3)
R4 = RobotId(4)
R5 = RobotId(5)
R6 = RobotId(6)
R7 = RobotId(7)

ALL_ROBOT_IDS: list[RobotId] = [R1, R2, R3, R4, R5, R6, R7]

# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------

ROBOTS: dict[RobotId, Robot] = {
    R1: Robot(
        id=R1,
        capabilities=frozenset({Capability.VISION, Capability.SENSING}),
    ),
    R2: Robot(
        id=R2,
        capabilities=frozenset({Capability.VISION, Capability.SENSING}),
    ),
    R3: Robot(
        id=R3,
        capabilities=frozenset({Capability.VISION, Capability.MANIPULATION}),
    ),
    R4: Robot(
        id=R4,
        capabilities=frozenset({Capability.VISION, Capability.MANIPULATION}),
    ),
    R5: Robot(
        id=R5,
        capabilities=frozenset({Capability.VISION, Capability.MANIPULATION}),
    ),
    R6: Robot(
        id=R6,
        capabilities=frozenset({Capability.VISION, Capability.MANIPULATION, Capability.REPAIR}),
    ),
    R7: Robot(
        id=R7,
        capabilities=frozenset({Capability.VISION, Capability.MANIPULATION}),
    ),
}

# ---------------------------------------------------------------------------
# Initial states
# ---------------------------------------------------------------------------

ROBOT_STATES: dict[RobotId, RobotState] = {
    R1: RobotState(robot_id=R1, position=Position(20, 2)),   # INSPECTION zone
    R2: RobotState(robot_id=R2, position=Position(6, 7)),    # west north, near Alpha
    R3: RobotState(robot_id=R3, position=Position(11, 9)),   # west north tier
    R4: RobotState(robot_id=R4, position=Position(5, 14)),   # west mid tier
    R5: RobotState(robot_id=R5, position=Position(30, 9)),   # east north, near Bravo
    R6: RobotState(robot_id=R6, position=Position(34, 14)),  # east mid tier
    R7: RobotState(robot_id=R7, position=Position(5, 27)),   # south staging, near LOADING
}
