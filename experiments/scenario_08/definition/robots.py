# Scenario 13 — Formation Requirement (MoveTask)
#
# 5 robots positioned near the left side of the grid, equidistant between
# both cargo objects. None are pre-assigned; the LLM must allocate them.

from __future__ import annotations

from simulation.domain import Robot, RobotState
from simulation.domain.robot_state import RobotId
from simulation.primitives import Capability, Position

R1 = RobotId(1)
R2 = RobotId(2)
R3 = RobotId(3)
R4 = RobotId(4)
R5 = RobotId(5)

ROBOTS: dict[RobotId, Robot] = {
    R1: Robot(id=R1, capabilities=frozenset({Capability.VISION})),
    R2: Robot(id=R2, capabilities=frozenset({Capability.VISION})),
    R3: Robot(id=R3, capabilities=frozenset({Capability.VISION})),
    R4: Robot(id=R4, capabilities=frozenset({Capability.VISION})),
    R5: Robot(id=R5, capabilities=frozenset({Capability.VISION})),
}

ROBOT_STATES: dict[RobotId, RobotState] = {
    R1: RobotState(robot_id=R1, position=Position(1, 4)),
    R2: RobotState(robot_id=R2, position=Position(2, 5)),
    R3: RobotState(robot_id=R3, position=Position(1, 7)),
    R4: RobotState(robot_id=R4, position=Position(2, 9)),
    R5: RobotState(robot_id=R5, position=Position(1, 10)),
}
