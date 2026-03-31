# Scenario 01 — Priority Override
#
# 2 robots starting on the left side of the map, close to structural tasks
# and far from the medical task. Without a priority rule, the LLM is likely
# to assign both robots to nearby structural tasks and ignore the medical one.

from __future__ import annotations

from simulation.domain import Robot, RobotState
from simulation.domain.robot_state import RobotId
from simulation.primitives import Capability, Position

R1 = RobotId(1)
R2 = RobotId(2)

ROBOTS: dict[RobotId, Robot] = {
    R1: Robot(id=R1, capabilities=frozenset({Capability.VISION})),
    R2: Robot(id=R2, capabilities=frozenset({Capability.VISION})),
}

ROBOT_STATES: dict[RobotId, RobotState] = {
    R1: RobotState(robot_id=R1, position=Position(2, 7)),
    R2: RobotState(robot_id=R2, position=Position(4, 7)),
}
