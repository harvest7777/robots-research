"""
Work Eligibility

Pure function for determining which robots are eligible to work on a task
in a given tick. No simulation state is held here — all inputs are explicit.
"""

from __future__ import annotations

from simulation_models.robot_state import RobotId
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.task import Task, TaskId
from simulation_models.task_state import TaskState, TaskStatus
from simulation_models.time import Time


def get_eligible_robots(
    task: Task,
    task_states: dict[TaskId, TaskState],
    robots: dict[RobotId, Robot],
    robot_states: dict[RobotId, RobotState],
    environment: Environment,
    time: Time,
) -> list[RobotId]:
    """Return IDs of robots eligible to work on task this tick.

    Returns empty list if the task is in a terminal state, past its
    deadline, or has unfinished dependencies. Otherwise filters
    task_states[task.id].assigned_robot_ids down to robots that
    satisfy all per-robot constraints (capabilities, battery, spatial).
    """
    task_state = task_states[task.id]

    if task_state.status in (TaskStatus.DONE, TaskStatus.FAILED):
        return []
    if task.deadline is not None and time.tick > task.deadline.tick:
        return []
    if any(task_states[dep].status != TaskStatus.DONE for dep in task.dependencies):
        return []

    eligible = []
    for robot_id in task_state.assigned_robot_ids:
        robot = robots[robot_id]
        state = robot_states[robot_id]

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
                zone = environment.get_zone(sc.target)
                if zone is None:
                    continue
                if zone.contains(state.position):
                    pass  # in zone, eligible
                elif sc.max_distance == 0:
                    continue
                else:
                    nearest_dist = min(
                        state.position.manhattan(cell) for cell in zone.cells
                    )
                    if nearest_dist > sc.max_distance:
                        continue

        eligible.append(robot_id)

    return eligible
