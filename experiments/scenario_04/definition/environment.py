# Scenario 04 — flat 20x15 grid with one rescue point hidden on the right side.
# The rescue point spawns a high-priority WorkTask when a searching robot finds it.

from simulation.domain import (
    Environment,
    RescuePoint,
    SpatialConstraint,
    TaskId,
    TaskState,
    WorkTask,
)
from simulation.primitives import Capability, Position, Time

RESCUE_POINT_ID = TaskId(6)

_rescue_task = WorkTask(
    id=RESCUE_POINT_ID,
    priority=10,
    required_work_time=Time(10),
    spatial_constraint=SpatialConstraint(target=Position(18, 7), max_distance=1),
    required_capabilities=frozenset({Capability.VISION}),
)

ENVIRONMENT = Environment(width=20, height=15)
ENVIRONMENT.add_rescue_point(RescuePoint(
    id=RESCUE_POINT_ID,
    name="Rescue Alpha",
    spatial_constraint=SpatialConstraint(target=Position(18, 7), max_distance=2),
    task=_rescue_task,
    initial_task_state=TaskState(task_id=RESCUE_POINT_ID),
))
