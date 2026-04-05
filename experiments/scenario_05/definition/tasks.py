# Scenario 05 — Sealed Room (Unreachable Task)
#
# T1_SEALED: priority 5, inside the fully enclosed room — unreachable.
#   Robots start just outside its left wall, so by priority and proximity
#   the naive assignment is to send all robots here.
#
# T2, T3, T4: priority 1, outside the sealed room — the correct assignments.
#
# Compliance check: does the LLM avoid assigning any robot to T1?

from __future__ import annotations

from experiments.models.task_spawn import SpawnTask
from simulation.domain import TaskId, WorkTask, SpatialConstraint
from simulation.primitives import Capability, Position, Time

T1_SEALED   = TaskId(1)
T2_OUTSIDE  = TaskId(2)
T3_OUTSIDE  = TaskId(3)
T4_OUTSIDE  = TaskId(4)

TASK_SPAWNS = [
    SpawnTask(task_to_spawn=WorkTask(
        id=T1_SEALED,
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(9, 4), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T2_OUTSIDE,
        priority=1,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(2, 11), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T3_OUTSIDE,
        priority=1,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(16, 4), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T4_OUTSIDE,
        priority=1,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(16, 11), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
]
