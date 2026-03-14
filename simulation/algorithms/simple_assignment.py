"""
Simple greedy assignment algorithm.

Assigns robots to tasks based on capability matching.
- Each robot can only be assigned to one task at a time
- Pass 1: first-fit assigns one capable robot to each task
- Pass 2: surplus robots are added to the first task they can support
"""

from simulation.domain.assignment import Assignment
from simulation.domain.base_task import BaseTask, TaskId
from simulation.domain.robot_state import RobotId
from simulation.domain.robot import Robot
from simulation.domain.task import Task, TaskType
from simulation.domain.search_task import SearchTask
from simulation.primitives.time import Time


def simple_assign(tasks: list[BaseTask], robots: list[Robot]) -> list[Assignment]:
    """
    Assign robots to tasks using a two-pass greedy algorithm.

    Pass 1: first-fit assigns one capable robot to each eligible task.
    Pass 2: any remaining unassigned robots are added to the first task
            they can support (so surplus capacity is not wasted).

    A robot can only be assigned to one task at a time.

    Special cases:
    - RESCUE tasks: skipped entirely; the simulation triggers rescue
      assignments automatically when a rescue point is found.
    - IDLE tasks: skipped entirely; they are placeholder no-ops.

    Args:
        tasks: List of tasks to assign robots to
        robots: List of available robots

    Returns:
        List of assignments mapping tasks to robots
    """
    robot_ids_by_task: dict[TaskId, set[RobotId]] = {}
    assigned_robots: set[RobotId] = set()

    # TODO: this is a bit noisy and not clear, why are these eligible
    # RESCUE and IDLE tasks not eligible? Although it is true, it is a
    # nuance to remember
    eligible = [
        t for t in tasks
        if isinstance(t, (Task, SearchTask))
        and not (isinstance(t, Task) and t.type in (TaskType.RESCUE, TaskType.IDLE))
    ]

    # Pass 1: assign one robot per task (first-fit)
    for task in eligible:
        for robot in robots:
            if robot.id in assigned_robots:
                continue
            if task.required_capabilities <= robot.capabilities:
                robot_ids_by_task[task.id] = {robot.id}
                assigned_robots.add(robot.id)
                break

    # Pass 2: add surplus robots to the first task they can support
    for robot in robots:
        if robot.id in assigned_robots:
            continue
        for task in eligible:
            if task.id not in robot_ids_by_task:
                continue
            if task.required_capabilities <= robot.capabilities:
                robot_ids_by_task[task.id].add(robot.id)
                assigned_robots.add(robot.id)
                break

    return [
        Assignment(task_id=task_id, robot_ids=frozenset(rids), assign_at=Time(0))
        for task_id, rids in robot_ids_by_task.items()
    ]
