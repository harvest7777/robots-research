from dataclasses import dataclass, field
from enum import Enum


class TaskType(Enum):
    ROUTINE_INSPECTION = "routine_inspection"
    ANOMALY_INVESTIGATION = "anomaly_investigation"
    PREVENTIVE_MAINTENANCE = "preventive_maintenance"
    EMERGENCY_RESPONSE = "emergency_response"


class TaskStatus(Enum):
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Task:
    id: str
    task_type: TaskType
    x: float
    y: float
    required_capabilities: set[str] = field(default_factory=set)
    duration_est_s: float = 60.0
    status: TaskStatus = TaskStatus.UNASSIGNED
    assigned_robot_id: str | None = None
    arrival_time_s: float = 0.0
    start_time_s: float | None = None
    completion_time_s: float | None = None

    @property
    def location(self) -> tuple[float, float]:
        return (self.x, self.y)

    def assign_to(self, robot_id: str, t_now: float):
        self.assigned_robot_id = robot_id
        self.status = TaskStatus.ASSIGNED

    def start_execution(self, t_now: float):
        self.status = TaskStatus.IN_PROGRESS
        self.start_time_s = t_now

    def complete(self, t_now: float):
        self.status = TaskStatus.DONE
        self.completion_time_s = t_now

    def fail(self, t_now: float):
        self.status = TaskStatus.FAILED
        self.completion_time_s = t_now
