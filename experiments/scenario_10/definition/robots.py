# Scenario 10 — Capability Mismatch Correction
#
# Multiple robots with different capabilities, multiple tasks with different requirements.
# Tests if LLM correctly matches robot capabilities to task requirements.
#
# Robots:
# - R1, R2: VISION only
# - R3, R4: MANIPULATION only
# - R5: VISION + MANIPULATION
# - R6: VISION + SENSING
#
# Tasks:
# - T1: MANIPULATION only (requires manipulation) — can only be done by R3, R4, R5
# - T2: VISION only (requires vision) — can be done by R1, R2, R5, R6
# - T3: SENSING only (requires sensing) — can only be done by R6
# - T4: VISION + MANIPULATION (requires both) — can only be done by R5
# - T5: VISION only, close to R1, R2 — easily completable
#
# Baseline behavior: LLM may assign wrong-capability robots to tasks, resulting in
# ignored assignments and no work done.
#
# With rule: "Only robots with required capabilities may be assigned"
#
# Success metric: Do assigned robots have required capabilities? Does work happen?

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
    R3: Robot(id=R3, capabilities=frozenset({Capability.MANIPULATION})),
    R4: Robot(id=R4, capabilities=frozenset({Capability.MANIPULATION})),
    R5: Robot(
        id=R5, capabilities=frozenset({Capability.VISION, Capability.MANIPULATION})
    ),
    R6: Robot(id=R6, capabilities=frozenset({Capability.VISION, Capability.SENSING})),
}

ROBOT_STATES: dict[RobotId, RobotState] = {
    R1: RobotState(robot_id=R1, position=Position(2, 7)),
    R2: RobotState(robot_id=R2, position=Position(4, 7)),
    R3: RobotState(robot_id=R3, position=Position(8, 7)),
    R4: RobotState(robot_id=R4, position=Position(10, 7)),
    R5: RobotState(robot_id=R5, position=Position(12, 7)),
    R6: RobotState(robot_id=R6, position=Position(14, 7)),
}
