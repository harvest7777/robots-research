"""
Simple greedy assignment algorithm.

Assigns robots to tasks based on capability matching.
- Each robot can only be assigned to one task at a time
- A task can have multiple robots assigned to it
- Uses first-fit: assigns the first available robot with required capabilities
"""

from simulation_models.assignment import Assignment, RobotId
from simulation_models.robot import Robot
from simulation_models.task import Task


def simple_assign(tasks: list[Task], robots: list[Robot]) -> list[Assignment]:
    """
    Assign robots to tasks using a simple greedy algorithm.

    For each task, finds the first available robot that has all required
    capabilities and assigns it. A robot can only be assigned to one task.

    Args:
        tasks: List of tasks to assign robots to
        robots: List of available robots

    Returns:
        List of assignments mapping tasks to robots
    """
    assignments: list[Assignment] = []
    assigned_robots: set[RobotId] = set()

    for task in tasks:
        for robot in robots:
            if robot.id in assigned_robots:
                continue

            if task.required_capabilities <= robot.capabilities:
                assignments.append(
                    Assignment(task_id=task.id, robot_ids=frozenset([robot.id]))
                )
                assigned_robots.add(robot.id)
                break

    return assignments