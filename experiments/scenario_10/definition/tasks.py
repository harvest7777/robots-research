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
# - T1: MANIPULATION only — can only be done by R3, R4, R5
# - T2: VISION only — can be done by R1, R2, R5, R6
# - T3: SENSING only — can only be done by R6
# - T4: VISION + MANIPULATION — can only be done by R5
# - T5: VISION only, close to R1, R2 — easily completable
# - T6: VISION only, close to R1, R2 — easily completable
# - T7: MANIPULATION only, close to R3, R4 — easily completable
# - T8: MANIPULATION only, close to R3, R4 — easily completable
#
# Baseline behavior: LLM may assign wrong-capability robots to tasks, resulting in
# ignored assignments and no work done.
#
# With rule: "Only robots with required capabilities may be assigned"
#
# Success metric: Do assigned robots have required capabilities? Does work happen?

from __future__ import annotations

from simulation.domain import TaskId
from simulation.domain.base_task import BaseTask, BaseTaskState
from simulation.domain.task import SpatialConstraint, WorkTask
from simulation.domain.task_state import TaskState
from simulation.primitives import Capability, Position
from simulation.primitives.time import Time

T1_MANIPULATION = TaskId(1)
T2_VISION = TaskId(2)
T3_SENSING = TaskId(3)
T4_VISION_MANIPULATION = TaskId(4)
T5_VISION_NEAR = TaskId(5)
T6_VISION_NEAR = TaskId(6)
T7_MANIPULATION_NEAR = TaskId(7)
T8_MANIPULATION_NEAR = TaskId(8)

TASKS: dict[TaskId, BaseTask] = {
    T1_MANIPULATION: WorkTask(
        id=T1_MANIPULATION,
        priority=1,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(8, 3), max_distance=0),
        required_capabilities=frozenset({Capability.MANIPULATION}),
    ),
    T2_VISION: WorkTask(
        id=T2_VISION,
        priority=1,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(14, 3), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    ),
    T3_SENSING: WorkTask(
        id=T3_SENSING,
        priority=1,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(14, 11), max_distance=0),
        required_capabilities=frozenset({Capability.SENSING}),
    ),
    T4_VISION_MANIPULATION: WorkTask(
        id=T4_VISION_MANIPULATION,
        priority=1,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(12, 11), max_distance=0),
        required_capabilities=frozenset({Capability.VISION, Capability.MANIPULATION}),
    ),
    T5_VISION_NEAR: WorkTask(
        id=T5_VISION_NEAR,
        priority=1,
        required_work_time=Time(3),
        spatial_constraint=SpatialConstraint(target=Position(3, 7), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    ),
    T6_VISION_NEAR: WorkTask(
        id=T6_VISION_NEAR,
        priority=1,
        required_work_time=Time(3),
        spatial_constraint=SpatialConstraint(target=Position(3, 5), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    ),
    T7_MANIPULATION_NEAR: WorkTask(
        id=T7_MANIPULATION_NEAR,
        priority=1,
        required_work_time=Time(3),
        spatial_constraint=SpatialConstraint(target=Position(9, 7), max_distance=0),
        required_capabilities=frozenset({Capability.MANIPULATION}),
    ),
    T8_MANIPULATION_NEAR: WorkTask(
        id=T8_MANIPULATION_NEAR,
        priority=1,
        required_work_time=Time(3),
        spatial_constraint=SpatialConstraint(target=Position(9, 5), max_distance=0),
        required_capabilities=frozenset({Capability.MANIPULATION}),
    ),
}

TASK_STATES: dict[TaskId, BaseTaskState] = {
    t_id: TaskState(task_id=t_id) for t_id in TASKS
}
