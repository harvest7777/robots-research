# Scenario 10 — Capability Mismatch Correction
#
# 2 VISION-only robots available. 1 task requires MANIPULATION capability.
# Without an override rule, the LLM may assign a VISION robot to the
# MANIPULATION task, which will fail (ignored due to WRONG_CAPABILITY).
#
# Baseline behavior: LLM assigns VISION robot to MANIPULATION task,
# no work is done because the robot lacks the required capability.
#
# With rule: "Only robots with required capabilities may be assigned"
#
# Compliance check: Does the assigned robot have the required capability?
# Does work happen?

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
