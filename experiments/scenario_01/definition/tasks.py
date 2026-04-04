# Scenario 01 — Priority Override
#
# 1 medical task (priority=10) placed far right — the LLM must send a robot
# there even though 3 structural tasks (priority=3) are sitting nearby.
#
# Baseline behaviour: LLM assigns by proximity → both robots go to structural
# tasks, medical task is ignored.
#
# With rule: "Tasks with priority 10 are critical medical rescues. Always
# assign at least one robot to the highest-priority task immediately,
# regardless of distance."
#
# Compliance check: was at least one robot assigned to T1 on the first step?

from __future__ import annotations

from experiments.models.task_spawn import SpawnTask
from simulation.domain import TaskId
from simulation.domain.task import SpatialConstraint, WorkTask
from simulation.primitives import Capability, Position
from simulation.primitives.time import Time

T1_MEDICAL    = TaskId(1)
T2_STRUCTURAL = TaskId(2)
T3_STRUCTURAL = TaskId(3)
T4_STRUCTURAL = TaskId(4)

TASK_SPAWNS = [
    SpawnTask(task_to_spawn=WorkTask(
        id=T1_MEDICAL,
        priority=10,
        required_work_time=Time(15),
        spatial_constraint=SpatialConstraint(target=Position(17, 7), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T2_STRUCTURAL,
        priority=3,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(2, 5), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T3_STRUCTURAL,
        priority=3,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(4, 5), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T4_STRUCTURAL,
        priority=3,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(3, 9), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
]
