from dataclasses import dataclass, field
from enum import Enum
import math


class RobotStatus(Enum):
    IDLE = "idle"
    MOVING = "moving"
    EXECUTING = "executing"


@dataclass
class Robot:
    id: str
    x: float
    y: float
    speed_mps: float
    capabilities: set[str] = field(default_factory=set)
    status: RobotStatus = RobotStatus.IDLE
    task_progress_s: float = 0.0
    total_distance_traveled: float = 0.0

    @property
    def pos(self) -> tuple[float, float]:
        return (self.x, self.y)

    def can_execute(self, required_capabilities: set[str]) -> bool:
        return required_capabilities.issubset(self.capabilities)

    def move_toward(self, target_x: float, target_y: float, dt: float) -> bool:
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist == 0:
            return True

        move_dist = self.speed_mps * dt

        if move_dist >= dist:
            self.total_distance_traveled += dist
            self.x = target_x
            self.y = target_y
            return True
        else:
            ratio = move_dist / dist
            self.x += dx * ratio
            self.y += dy * ratio
            self.total_distance_traveled += move_dist
            return False

    def work_on_task(self, dt: float) -> float:
        self.task_progress_s += dt
        return self.task_progress_s

    def start_task(self):
        self.status = RobotStatus.MOVING
        self.task_progress_s = 0.0

    def begin_execution(self):
        self.status = RobotStatus.EXECUTING

    def finish_task(self):
        self.status = RobotStatus.IDLE
        self.task_progress_s = 0.0
