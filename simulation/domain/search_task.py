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

from dataclasses import dataclass

from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId


@dataclass(frozen=True)
class SearchTaskState(BaseTaskState):
    """
    Immutable runtime state for a SearchTask.

    Extends BaseTaskState (task_id, status, completed_at) with:
    - rescue_found: set of rescue point IDs discovered so far

    The engine marks this task DONE explicitly when all rescue points in the
    environment have been found. State does not self-transition.
    """

    rescue_found: frozenset[TaskId] = frozenset()


@dataclass(frozen=True)
class SearchTask(BaseTask):
    """
    Immutable description of a search-phase task.

    Fields inherited from BaseTask:
        id, priority, required_capabilities, dependencies

    SearchTask has no required_work_time (completion is event-driven) and
    no spatial_constraint (robots roam freely until a rescue point is found).
    Proximity-lock radius is controlled per rescue point via
    RescuePoint.spatial_constraint.max_distance.
    """

    def initial_state(self) -> SearchTaskState:
        return SearchTaskState(task_id=self.id, rescue_found=frozenset())
