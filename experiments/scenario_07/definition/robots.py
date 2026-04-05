# Scenario 11 — Bottleneck Congestion
#
# 6 robots lined up in front of the bottleneck entrance.
# They must pass through the single-cell entrance (8,7) to reach tasks inside.

from __future__ import annotations

from simulation.domain import Robot, RobotState
from simulation.domain.robot_state import RobotId
from simulation.primitives import Capability, Position

R1 = RobotId(1)
R2 = RobotId(2)
R3 = RobotId(3)
R4 = RobotId(4)
R5 = RobotId(5)
R6 = RobotId(6)

ROBOTS: dict[RobotId, Robot] = {
    R1: Robot(id=R1, capabilities=frozenset({Capability.VISION})),
    R2: Robot(id=R2, capabilities=frozenset({Capability.VISION})),
    R3: Robot(id=R3, capabilities=frozenset({Capability.VISION})),
    R4: Robot(id=R4, capabilities=frozenset({Capability.VISION})),
    R5: Robot(id=R5, capabilities=frozenset({Capability.VISION})),
    R6: Robot(id=R6, capabilities=frozenset({Capability.VISION})),
}

ROBOT_STATES: dict[RobotId, RobotState] = {
    R1: RobotState(robot_id=R1, position=Position(2, 6)),
    R2: RobotState(robot_id=R2, position=Position(3, 6)),
    R3: RobotState(robot_id=R3, position=Position(4, 6)),
    R4: RobotState(robot_id=R4, position=Position(5, 7)),
    R5: RobotState(robot_id=R5, position=Position(2, 7)),
    R6: RobotState(robot_id=R6, position=Position(3, 7)),
}
