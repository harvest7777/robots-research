"""
SearchTask and SearchTaskState definitions.

SearchTask describes a search-and-rescue search phase: robots roam the
environment looking for rescue points. It is triggered via the assignment
service like any other task, but its completion is event-driven (all rescue
points found) rather than work-accumulation-driven.

SearchTaskState tracks which rescue points have been found. Completion is
explicit: the engine calls mark_done when all rescue_found values are True.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
from simulation.domain.rescue_point import RescuePointId


@dataclass(frozen=True)
class SearchTask(BaseTask):
    """
    Immutable description of a search-phase task.

    Extends BaseTask with the proximity threshold at which a searching robot
    locks onto a nearby rescue point and navigates directly to it.

    Fields inherited from BaseTask:
        id, priority, required_capabilities, dependencies

    SearchTask has no required_work_time (completion is event-driven) and
    no spatial_constraint (robots roam freely until a rescue point is found).
    """

    proximity_threshold: int = 10


@dataclass
class SearchTaskState(BaseTaskState):
    """
    Mutable runtime state for a SearchTask.

    Extends BaseTaskState (task_id, status, completed_at) with:
    - rescue_found: tracks discovery status for each rescue point in scope

    The engine marks this task DONE explicitly when all rescue_found values
    are True. State does not self-transition.
    """

    rescue_found: dict[RescuePointId, bool] = field(default_factory=dict)
