"""
Simple greedy assignment algorithm.

Assigns robots to tasks based on capability matching.
- Each robot can only be assigned to one task at a time
- A task can have multiple robots assigned to it
- Uses first-fit: assigns the first available robot with required capabilities
"""

from simulation_models.assignment import Assignment
from simulation_models.robot_state import RobotId
from simulation_models.robot import Robot
from simulation_models.task import Task, TaskType
from simulation_models.time import Time


def simple_assign(tasks: list[Task], robots: list[Robot]) -> list[Assignment]:
    """
    Assign robots to tasks using a simple greedy algorithm.

    For each task, finds the first available robot that has all required
    capabilities and assigns it. A robot can only be assigned to one task.

    Special cases:
    - SEARCH tasks: all capable unassigned robots are assigned together
      (search is collaborative — every available robot participates).
    - RESCUE tasks: skipped entirely; the simulation triggers rescue
      assignments automatically when a rescue point is found.

    Args:
        tasks: List of tasks to assign robots to
        robots: List of available robots

    Returns:
        List of assignments mapping tasks to robots
    """
    assignments: list[Assignment] = []
    assigned_robots: set[RobotId] = set()

    for task in tasks:
        if task.type == TaskType.RESCUE:
            continue

        if task.type == TaskType.SEARCH:
            # Assign all unassigned capable robots to the search task together
            robot_ids = frozenset(
                robot.id
                for robot in robots
                if robot.id not in assigned_robots
                and task.required_capabilities <= robot.capabilities
            )
            if robot_ids:
                assignments.append(
                    Assignment(task_id=task.id, robot_ids=robot_ids, assign_at=Time(0))
                )
                assigned_robots.update(robot_ids)
            continue

        for robot in robots:
            if robot.id in assigned_robots:
                continue

            # LLM Part in the future
            if task.required_capabilities <= robot.capabilities:
                assignments.append(
                    Assignment(task_id=task.id, robot_ids=frozenset([robot.id]), assign_at=Time(0))
                )
                assigned_robots.add(robot.id)
                break

    return assignments