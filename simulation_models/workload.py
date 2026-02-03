import random
from dataclasses import dataclass, field
from .task import Task, TaskType


@dataclass
class WorkloadGenerator:
    env_width: float
    env_height: float
    task_types: list[TaskType] = field(default_factory=lambda: list(TaskType))
    capability_pool: list[str] = field(default_factory=lambda: ["inspect", "repair", "collect_data"])

    def generate_fixed_batch(
        self,
        num_tasks: int,
        arrival_time: float = 0.0,
        seed: int | None = None
    ) -> list[Task]:
        if seed is not None:
            random.seed(seed)

        tasks = []
        for i in range(num_tasks):
            task_type = random.choice(self.task_types)
            x = random.uniform(0, self.env_width)
            y = random.uniform(0, self.env_height)
            num_caps = random.randint(1, min(2, len(self.capability_pool)))
            required_caps = set(random.sample(self.capability_pool, num_caps))
            duration = self._duration_for_type(task_type)

            task = Task(
                id=f"task_{i}",
                task_type=task_type,
                x=x,
                y=y,
                required_capabilities=required_caps,
                duration_est_s=duration,
                arrival_time_s=arrival_time,
            )
            tasks.append(task)

        return tasks

    def _duration_for_type(self, task_type: TaskType) -> float:
        base_durations = {
            TaskType.ROUTINE_INSPECTION: 30.0,
            TaskType.ANOMALY_INVESTIGATION: 60.0,
            TaskType.PREVENTIVE_MAINTENANCE: 120.0,
            TaskType.EMERGENCY_RESPONSE: 45.0,
        }
        base = base_durations.get(task_type, 60.0)
        return base * random.uniform(0.8, 1.2)
