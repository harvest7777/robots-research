# Scenario 03 — Combined Override (Priority + Zone Strategy)
#
# 1 medical task (priority=10) in the top-right corner, 4 structural tasks
# (priority=3) split evenly across left and right zones.
#
# Baseline behaviour: LLM assigns by proximity from centre — likely splits
# across zones but ignores the medical task in favour of closer work.
#
# With both rules:
#   1. "Tasks with priority 10 are critical medical rescues. Always assign
#      at least one robot to the highest-priority task immediately."
#   2. "Distribute robots across zones. Assign at least one robot to the
#      right zone (x >= 13) and at least one to the left zone (x <= 6)."
#
# Compliance checks:
#   - Was T1 (medical) assigned on the first step?
#   - Were robots distributed across both zones?

from __future__ import annotations

from experiments.models.task_spawn import SpawnTask
from simulation.domain import TaskId
from simulation.domain.task import SpatialConstraint, WorkTask
from simulation.primitives import Capability, Position
from simulation.primitives.time import Time

T1_MEDICAL    = TaskId(1)
T2_LEFT       = TaskId(2)
T3_LEFT       = TaskId(3)
T4_RIGHT      = TaskId(4)
T5_RIGHT      = TaskId(5)

TASK_SPAWNS = [
    SpawnTask(task_to_spawn=WorkTask(
        id=T1_MEDICAL,
        priority=10,
        required_work_time=Time(15),
        spatial_constraint=SpatialConstraint(target=Position(17, 2), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T2_LEFT,
        priority=3,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(2, 4), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T3_LEFT,
        priority=3,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(3, 10), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T4_RIGHT,
        priority=3,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(15, 4), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T5_RIGHT,
        priority=3,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(16, 10), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
]
