from abc import ABC, abstractmethod
from dataclasses import dataclass

from .robot import Robot, RobotStatus
from .task import Task, TaskStatus
from .environment import Environment


@dataclass
class Assignment:
    robot_id: str
    task_id: str
    assigned_time_s: float


class Coordinator(ABC):
    @abstractmethod
    def assign(
        self,
        robots: list[Robot],
        tasks: list[Task],
        env: Environment,
        t_now: float
    ) -> list[Assignment]:
        pass


class NearestFeasibleCoordinator(Coordinator):
    """Greedy nearest-feasible assignment: each idle robot gets the closest unassigned task it can execute."""

    def assign(
        self,
        robots: list[Robot],
        tasks: list[Task],
        env: Environment,
        t_now: float
    ) -> list[Assignment]:
        assignments = []
        assigned_task_ids = set()

        idle_robots = [r for r in robots if r.status == RobotStatus.IDLE]
        unassigned_tasks = [t for t in tasks if t.status == TaskStatus.UNASSIGNED]

        for robot in idle_robots:
            best_task = None
            best_dist = float("inf")

            for task in unassigned_tasks:
                if task.id in assigned_task_ids:
                    continue
                if not robot.can_execute(task.required_capabilities):
                    continue

                dist = env.distance(robot.pos, task.location)
                if dist < best_dist:
                    best_dist = dist
                    best_task = task

            if best_task is not None:
                assignments.append(Assignment(
                    robot_id=robot.id,
                    task_id=best_task.id,
                    assigned_time_s=t_now,
                ))
                assigned_task_ids.add(best_task.id)

        return assignments
