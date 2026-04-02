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

from simulation.domain import TaskId
from simulation.domain.base_task import BaseTask, BaseTaskState
from simulation.domain.task import SpatialConstraint, WorkTask
from simulation.domain.task_state import TaskState
from simulation.primitives import Capability, Position
from simulation.primitives.time import Time

T1_MANIPULATION = TaskId(1)

TASKS: dict[TaskId, BaseTask] = {
    T1_MANIPULATION: WorkTask(
        id=T1_MANIPULATION,
        priority=1,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(10, 7), max_distance=0),
        required_capabilities=frozenset({Capability.MANIPULATION}),
    ),
}

TASK_STATES: dict[TaskId, BaseTaskState] = {
    t_id: TaskState(task_id=t_id) for t_id in TASKS
}
