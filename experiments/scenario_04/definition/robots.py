# Scenario 04 — Late Search-and-Rescue Interrupt
#
# 5 robots spread across the map, all with VISION capability.
# They begin working regular tasks at tick 0. A search-and-rescue
# task arrives at tick 15, which should pull robots off ongoing work.

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
    R1: RobotState(robot_id=R1, position=Position(3, 3)),
    R2: RobotState(robot_id=R2, position=Position(3, 11)),
    R3: RobotState(robot_id=R3, position=Position(10, 7)),
    R4: RobotState(robot_id=R4, position=Position(16, 3)),
    R5: RobotState(robot_id=R5, position=Position(16, 11)),
}
