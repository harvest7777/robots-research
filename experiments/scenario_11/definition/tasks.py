# Scenario 11 — Bottleneck Congestion
#
# Tasks inside the box (must pass through bottleneck):
# - T1, T2, T3: Close to entrance, easy to reach
# - T4, T5: Deep inside box, require traveling through bottleneck
#
# Tasks outside (no bottleneck):
# - T6, T7: Outside the box, easily accessible

from __future__ import annotations

from simulation.domain import TaskId
from simulation.domain.base_task import BaseTask, BaseTaskState
from simulation.domain.task import SpatialConstraint, WorkTask
from simulation.domain.task_state import TaskState
from simulation.primitives import Capability, Position
from simulation.primitives.time import Time

T1_INSIDE_NEAR = TaskId(1)
T2_INSIDE_NEAR = TaskId(2)
T3_INSIDE_NEAR = TaskId(3)
T4_INSIDE_DEEP = TaskId(4)
T5_INSIDE_DEEP = TaskId(5)
T6_OUTSIDE_NEAR = TaskId(6)
T7_OUTSIDE_NEAR = TaskId(7)

TASKS: dict[TaskId, BaseTask] = {
    T1_INSIDE_NEAR: WorkTask(
        id=T1_INSIDE_NEAR,
        priority=1,
        required_work_time=Time(3),
        spatial_constraint=SpatialConstraint(target=Position(9, 6), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    ),
    T2_INSIDE_NEAR: WorkTask(
        id=T2_INSIDE_NEAR,
        priority=1,
        required_work_time=Time(3),
        spatial_constraint=SpatialConstraint(target=Position(10, 7), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    ),
    T3_INSIDE_NEAR: WorkTask(
        id=T3_INSIDE_NEAR,
        priority=1,
        required_work_time=Time(3),
        spatial_constraint=SpatialConstraint(target=Position(9, 8), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    ),
    T4_INSIDE_DEEP: WorkTask(
        id=T4_INSIDE_DEEP,
        priority=1,
        required_work_time=Time(3),
        spatial_constraint=SpatialConstraint(target=Position(12, 6), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    ),
    T5_INSIDE_DEEP: WorkTask(
        id=T5_INSIDE_DEEP,
        priority=1,
        required_work_time=Time(3),
        spatial_constraint=SpatialConstraint(target=Position(12, 8), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    ),
    T6_OUTSIDE_NEAR: WorkTask(
        id=T6_OUTSIDE_NEAR,
        priority=1,
        required_work_time=Time(3),
        spatial_constraint=SpatialConstraint(target=Position(6, 5), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    ),
    T7_OUTSIDE_NEAR: WorkTask(
        id=T7_OUTSIDE_NEAR,
        priority=1,
        required_work_time=Time(3),
        spatial_constraint=SpatialConstraint(target=Position(6, 9), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    ),
}

TASK_STATES: dict[TaskId, BaseTaskState] = {
    t_id: TaskState(task_id=t_id) for t_id in TASKS
}
