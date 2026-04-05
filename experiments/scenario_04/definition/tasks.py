# Scenario 04 — Late Search-and-Rescue Interrupt
#
# Regular tasks (tick 0, priority 1, 20 ticks each):
# - T1–T4: WorkTasks spread across the map; all robots can handle these.
#
# Search-and-rescue task (tick 15, priority 10):
# - T5: SearchTask — robots must roam to find the rescue point (Rescue Alpha).
#   When found, the rescue point spawns T6 (WorkTask, priority 10) into the
#   active task set. T6 is defined in environment.py alongside the RescuePoint.
#
# Compliance check: does the LLM redirect at least one robot to the
# SearchTask when it appears at tick 15, despite ongoing regular work?

from __future__ import annotations

from experiments.models.task_spawn import SpawnTask
from simulation.domain import SearchTask, SearchTaskState, TaskId, WorkTask, SpatialConstraint
from simulation.primitives import Capability, Position, Time

T1_REGULAR = TaskId(1)
T2_REGULAR = TaskId(2)
T3_REGULAR = TaskId(3)
T4_REGULAR = TaskId(4)
T5_SEARCH  = TaskId(5)
RESCUE_POINT_ID = TaskId(6)

_rescue_task = WorkTask(
    id=RESCUE_POINT_ID,
    priority=10,
    required_work_time=Time(10),
    spatial_constraint=SpatialConstraint(target=Position(18, 7), max_distance=1),
    required_capabilities=frozenset({Capability.VISION}),
)

TASK_SPAWNS = [
    SpawnTask(task_to_spawn=WorkTask(
        id=T1_REGULAR,
        priority=1,
        required_work_time=Time(20),
        spatial_constraint=SpatialConstraint(target=Position(3, 3), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T2_REGULAR,
        priority=1,
        required_work_time=Time(20),
        spatial_constraint=SpatialConstraint(target=Position(3, 11), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T3_REGULAR,
        priority=1,
        required_work_time=Time(20),
        spatial_constraint=SpatialConstraint(target=Position(10, 7), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(task_to_spawn=WorkTask(
        id=T4_REGULAR,
        priority=1,
        required_work_time=Time(20),
        spatial_constraint=SpatialConstraint(target=Position(16, 3), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )),
    SpawnTask(
        task_to_spawn=SearchTask(
            id=T5_SEARCH,
            priority=10,
            required_capabilities=frozenset({Capability.VISION}),
        ),
        time_to_spawn=Time(10),
        task_state=SearchTaskState(task_id=T5_SEARCH),
    ),
]
