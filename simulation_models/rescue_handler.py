"""
Rescue Handler

Pure function for computing the effect of a rescue point being found.
Returns a RescueEffect describing all state changes required — the caller
is responsible for applying them. No state is mutated here.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation_models.assignment import Assignment, RobotId
from simulation_models.rescue_point import RescuePoint
from simulation_models.task import Task, TaskId, TaskType
from simulation_models.time import Time


@dataclass
class RescueEffect:
    """All state changes triggered by a rescue point being found.

    Attributes:
        rescue_found_updates: Mapping of rescue point IDs to set to True.
        new_assignment:       Assignment to register with the assignment service.
        tasks_to_mark_done:   IDs of SEARCH tasks to mark as DONE.
        waypoints_to_clear:   IDs of robots whose current_waypoint should be set to None.
    """

    rescue_found_updates: dict
    new_assignment: Assignment
    tasks_to_mark_done: list[TaskId]
    waypoints_to_clear: list[RobotId]


def compute_rescue_effect(
    rescue_point: RescuePoint,
    robot_to_task: dict[RobotId, TaskId],
    task_by_id: dict[TaskId, Task],
    tasks: list[Task],
    t_now: Time,
) -> RescueEffect:
    """Compute the full effect of a rescue point being found.

    All inputs are read-only. The returned RescueEffect describes every
    state change required; the caller (Simulation._step) applies them.
    """
    search_robot_ids = [
        rid for rid, tid in robot_to_task.items()
        if task_by_id[tid].type == TaskType.SEARCH
    ]

    search_task_ids = [
        task.id for task in tasks
        if task.type == TaskType.SEARCH
    ]

    return RescueEffect(
        rescue_found_updates={rescue_point.id: True},
        new_assignment=Assignment(
            task_id=rescue_point.rescue_task_id,
            robot_ids=frozenset(search_robot_ids),
            assign_at=t_now,
        ),
        tasks_to_mark_done=search_task_ids,
        waypoints_to_clear=search_robot_ids,
    )
