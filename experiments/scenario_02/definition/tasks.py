# Scenario 02 — Zone Strategy Override
#
# 4 tasks of equal priority split across two zones:
#   Left zone  (x <= 6):  T1, T2
#   Right zone (x >= 13): T3, T4
#
# Baseline behaviour: all 3 robots assigned to left-zone tasks (proximity),
# right zone tasks are delayed or never started.
#
# With rule: "Distribute robots across zones. Always assign at least one robot
# to the right zone (x >= 13) and at least one to the left zone (x <= 6)."
#
# Compliance check: was at least one robot assigned to a right-zone task
# on the first step?

from __future__ import annotations

from experiments.models.task_spawn import SpawnTask
from simulation.domain import TaskId
from simulation.domain.task import SpatialConstraint, WorkTask
from simulation.primitives import Capability, Position
from simulation.primitives.time import Time

T1_LEFT  = TaskId(1)
T2_LEFT  = TaskId(2)
T3_RIGHT = TaskId(3)
T4_RIGHT = TaskId(4)

TASK_SPAWNS = [
    SpawnTask(task_to_spawn=WorkTask(
        id=T1_LEFT,
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(2, 4), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T2_LEFT,
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(4, 10), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T3_RIGHT,
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(14, 4), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T4_RIGHT,
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(16, 10), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
]
