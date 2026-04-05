# Scenario 05 — Sealed Room (Unreachable Task)
#
# 3 robots placed just outside the left wall of the sealed room.
# Without knowledge of the blockage they would be assigned to T1
# (highest priority, geographically closest).

from __future__ import annotations

from simulation.domain import Robot, RobotState
from simulation.domain.robot_state import RobotId
from simulation.primitives import Capability, Position

R1 = RobotId(1)
R2 = RobotId(2)
R3 = RobotId(3)

ROBOTS: dict[RobotId, Robot] = {
    R1: Robot(id=R1, capabilities=frozenset({Capability.VISION})),
    R2: Robot(id=R2, capabilities=frozenset({Capability.VISION})),
    R3: Robot(id=R3, capabilities=frozenset({Capability.VISION})),
}

ROBOT_STATES: dict[RobotId, RobotState] = {
    R1: RobotState(robot_id=R1, position=Position(3, 3)),
    R2: RobotState(robot_id=R2, position=Position(3, 4)),
    R3: RobotState(robot_id=R3, position=Position(3, 5)),
}
