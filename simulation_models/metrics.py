from dataclasses import dataclass, field

from .robot import Robot
from .task import Task, TaskStatus


@dataclass
class SimulationMetrics:
    completed_tasks: list[Task] = field(default_factory=list)
    failed_tasks: list[Task] = field(default_factory=list)

    @property
    def makespan_s(self) -> float:
        if not self.completed_tasks:
            return 0.0
        return max(t.completion_time_s for t in self.completed_tasks if t.completion_time_s is not None)

    @property
    def avg_task_completion_time_s(self) -> float:
        if not self.completed_tasks:
            return 0.0
        completion_times = [
            t.completion_time_s - t.arrival_time_s
            for t in self.completed_tasks
            if t.completion_time_s is not None
        ]
        return sum(completion_times) / len(completion_times)

    def total_travel_distance_m(self, robots: list[Robot]) -> float:
        return sum(r.total_distance_traveled for r in robots)

    def record_task_done(self, task: Task):
        if task.status == TaskStatus.DONE:
            self.completed_tasks.append(task)
        elif task.status == TaskStatus.FAILED:
            self.failed_tasks.append(task)

    def summary(self, robots: list[Robot]) -> dict:
        return {
            "makespan_s": self.makespan_s,
            "avg_task_completion_time_s": self.avg_task_completion_time_s,
            "total_travel_distance_m": self.total_travel_distance_m(robots),
            "tasks_completed": len(self.completed_tasks),
            "tasks_failed": len(self.failed_tasks),
        }
