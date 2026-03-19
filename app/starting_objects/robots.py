# R1-R2: scouts (VISION + SENSING)
# R3-R7: carriers (VISION + MANIPULATION); R6 also has REPAIR
# Placed near their respective casualties so formations can assemble quickly.

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
    R1: RobotState(robot_id=R1, position=Position(20, 2)),   # north-center
    R2: RobotState(robot_id=R2, position=Position(6, 7)),    # near Alpha
    R3: RobotState(robot_id=R3, position=Position(11, 9)),   # near Alpha
    R4: RobotState(robot_id=R4, position=Position(5, 14)),   # near Charlie
    R5: RobotState(robot_id=R5, position=Position(30, 9)),   # near Bravo
    R6: RobotState(robot_id=R6, position=Position(34, 14)),  # near Delta
    R7: RobotState(robot_id=R7, position=Position(5, 27)),   # near Echo
}
