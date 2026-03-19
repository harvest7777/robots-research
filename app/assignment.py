"""
app/assignment.py

Greedy task assignment algorithm.

For each robot, assigns it to the highest-priority task it is capable of
doing that still has open slots.  Run this whenever a task completes (robots
freed) or a new task spawns (higher-priority work available).

Slot budget per task type:
  MoveTask   — min_robots_required (exactly that many, no more)
  SearchTask — unlimited (more searchers = faster coverage)
  WorkTask   — 1 robot (single-occupancy)
"""

from __future__ import annotations

from simulation.domain import Assignment
from simulation.domain.base_task import TaskId
from simulation.domain.move_task import MoveTask
from simulation.domain.search_task import SearchTask
from simulation.domain.simulation_state import SimulationState


def _slots(task, assigned: int) -> int:
    if isinstance(task, MoveTask):
        return max(0, task.min_robots_required - assigned)
    if isinstance(task, SearchTask):
        return 999
    return max(0, 1 - assigned)  # WorkTask


def greedy_assign(state: SimulationState) -> list[Assignment]:
    """Return assignments for all robots based on current task priorities."""
    available = sorted(
        [t for t in state.tasks.values() if state.task_states[t.id].status is None],
        key=lambda t: t.priority,
        reverse=True,
    )

    assigned_count: dict[TaskId, int] = {}
    result: list[Assignment] = []

    for robot_id, robot in state.robots.items():
        for task in available:
            if _slots(task, assigned_count.get(task.id, 0)) <= 0:
                continue
            if task.required_capabilities <= robot.capabilities:
                result.append(Assignment(task_id=task.id, robot_id=robot_id))
                assigned_count[task.id] = assigned_count.get(task.id, 0) + 1
                break

    return result
