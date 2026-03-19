"""
Task Definition Module

A Task is an immutable, declarative description of a work-accumulation goal:
what outcome is required, where it must happen, what prerequisites it needs,
and how many robots are needed.

WorkTask extends BaseTask with fields specific to work-accumulation tasks.
Search behaviour lives in SearchTask; object-carry lives in MoveTask.

Design principles:
- WorkTask describes intent and constraints only
- WorkTask is immutable (frozen dataclass, frozenset for collections)
- WorkTask contains NO execution state (no progress, timestamps, assigned robots)
- WorkTask is serializable and replayable (IDs, enums, value objects only)
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.primitives.capability import Capability  # noqa: F401 (re-export via BaseTask)
from simulation.primitives.position import Position
from simulation.primitives.time import Time
from simulation.primitives.zone import ZoneId

from simulation.domain.base_task import BaseTask, TaskId, TaskStatus  # noqa: F401 (re-export)
from simulation.domain.task_state import TaskState


@dataclass(frozen=True)
class SpatialConstraint:
    """
    Describes where a task must be satisfied.

    Does not imply execution steps or contain environment logic.
    """

    target: Position | ZoneId
    max_distance: int = 0  # 0 = exact, > 0 = within distance


@dataclass(frozen=True)
class WorkTask(BaseTask):
    """
    Immutable description of any task that completes by accumulating
    robot-ticks of work at a spatial location.

    Task type is identified by isinstance checks, not enums. Use WorkTask
    directly for generic work-accumulation; use SearchTask, MoveTask, or
    RescuePoint for specialised task kinds.
    """

    required_work_time: Time = Time(0)
    spatial_constraint: SpatialConstraint | None = None
    deadline: Time | None = None
    min_robots_needed: int = 1

    def initial_state(self) -> TaskState:
        return TaskState(task_id=self.id)
