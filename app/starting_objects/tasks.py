"""
app/tasks.py

Initial tasks for the 40×30 disaster-response environment.

The five MoveTasks are NOT listed here — they are spawned dynamically
when robots discover their corresponding RescuePoints.  Only the tasks
that exist from tick 0 are defined below.

Task roster
-----------
  SearchTask      (id=1)  — all robots with VISION sweep the map until all
                            five casualties are found.
  InspectionTask  (id=2)  — VISION + SENSING required; scouts (R1, R2) are
                            the only robots that can satisfy this alone.
                            Located inside the INSPECTION zone.
  MaintenanceTask (id=3)  — VISION + REPAIR required; only the east
                            specialist (R6) carries REPAIR.  Located inside
                            the MAINTENANCE zone in the south-east staging
                            area — robots must route through the x=32-33
                            corridor to reach it.
"""

from __future__ import annotations

from simulation.domain import SearchTask, SpatialConstraint, TaskId, WorkTask
from simulation.domain.base_task import BaseTask, BaseTaskState
from simulation.domain.search_task import SearchTaskState
from simulation.domain.task_state import TaskState
from simulation.primitives import Capability, Position, Time

# ---------------------------------------------------------------------------
# Task IDs
# ---------------------------------------------------------------------------

SEARCH_TASK_ID = TaskId(1)
INSPECTION_TASK_ID = TaskId(2)
MAINTENANCE_TASK_ID = TaskId(3)

# ---------------------------------------------------------------------------
# Task definitions
# ---------------------------------------------------------------------------

TASKS: dict[TaskId, BaseTask] = {
    SEARCH_TASK_ID: SearchTask(
        id=SEARCH_TASK_ID,
        priority=5,
        required_capabilities=frozenset({Capability.VISION}),
    ),
    INSPECTION_TASK_ID: WorkTask(
        id=INSPECTION_TASK_ID,
        priority=3,
        required_work_time=Time(35),
        spatial_constraint=SpatialConstraint(target=Position(19, 3), max_distance=0),
        required_capabilities=frozenset({Capability.VISION, Capability.SENSING}),
    ),
    MAINTENANCE_TASK_ID: WorkTask(
        id=MAINTENANCE_TASK_ID,
        priority=3,
        required_work_time=Time(50),
        spatial_constraint=SpatialConstraint(target=Position(35, 25), max_distance=0),
        required_capabilities=frozenset({Capability.VISION, Capability.REPAIR}),
    ),
}

# ---------------------------------------------------------------------------
# Initial task states
# ---------------------------------------------------------------------------

TASK_STATES: dict[TaskId, BaseTaskState] = {
    SEARCH_TASK_ID: SearchTaskState(task_id=SEARCH_TASK_ID),
    INSPECTION_TASK_ID: TaskState(task_id=INSPECTION_TASK_ID),
    MAINTENANCE_TASK_ID: TaskState(task_id=MAINTENANCE_TASK_ID),
}
