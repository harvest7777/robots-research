# Scenario 03 — Combined Override (Priority + Zone Strategy)
#
# 3 robots starting in the centre of the map. Both override rules apply
# simultaneously, testing whether the LLM can satisfy two constraints at once.

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
    R1: RobotState(robot_id=R1, position=Position(9, 6)),
    R2: RobotState(robot_id=R2, position=Position(10, 7)),
    R3: RobotState(robot_id=R3, position=Position(9, 8)),
}
