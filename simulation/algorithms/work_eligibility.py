"""
Work Eligibility

Pure function for determining which robots are eligible to work on a task
in a given tick. No simulation state is held here — all inputs are explicit.
"""

from __future__ import annotations

from simulation.primitives.position import Position
from simulation.domain.robot_state import RobotId
from simulation.domain.step_context import StepContext
from simulation.domain.task import Task
from simulation.domain.task_state import TaskStatus


def filter_assignments_for_eligible_robots(task: Task, ctx: StepContext) -> list[RobotId]:
    """Return IDs of robots eligible to work on task this tick.

    Returns empty list if the task is in a terminal state, past its
    deadline, or has unfinished dependencies. Otherwise filters the
    robots currently assigned to this task (derived from ctx.robot_to_task)
    down to those that satisfy all per-robot constraints (capabilities,
    battery, spatial).
    """
    task_state = ctx.task_states[task.id]

    if task_state.status in (TaskStatus.DONE, TaskStatus.FAILED):
        return []
    if task.deadline is not None and ctx.t_now.tick > task.deadline.tick:
        return []
    if any(ctx.task_states[dep].status != TaskStatus.DONE for dep in task.dependencies):
        return []

    eligible = []
    for robot_id in (rid for a in ctx.assignments if a.task_id == task.id for rid in a.robot_ids):
        robot = ctx.robot_by_id[robot_id]
        state = ctx.robot_states[robot_id]

        if state.battery_level <= 0.0:
            continue
        if not task.required_capabilities.issubset(robot.capabilities):
            continue
        if task.spatial_constraint is not None:
            sc = task.spatial_constraint
            if isinstance(sc.target, Position):
                dist = state.position.manhattan(sc.target)
                tolerance = sc.max_distance if sc.max_distance > 0 else 0
                if dist > tolerance:
                    continue
            else:
                zone = ctx.environment.get_zone(sc.target)
                if zone is None:
                    continue
                if not zone.contains(state.position):
                    if sc.max_distance == 0:
                        continue
                    nearest_dist = min(
                        state.position.manhattan(cell) for cell in zone.cells
                    )
                    if nearest_dist > sc.max_distance:
                        continue

        eligible.append(robot_id)

    return eligible
