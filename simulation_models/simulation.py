from dataclasses import dataclass, field

from .environment import Environment
from .robot import Robot, RobotStatus
from .task import Task, TaskStatus
from .coordinator import Coordinator, Assignment
from .metrics import SimulationMetrics


@dataclass
class Simulation:
    env: Environment
    robots: list[Robot]
    tasks: list[Task]
    coordinator: Coordinator
    dt: float = 1.0
    t_now: float = 0.0
    metrics: SimulationMetrics = field(default_factory=SimulationMetrics)
    assignments: dict[str, Assignment] = field(default_factory=dict)  # robot_id -> Assignment

    def step(self):
        self._run_allocation()
        self._update_robots()
        self.t_now += self.dt

    def _run_allocation(self):
        new_assignments = self.coordinator.assign(self.robots, self.tasks, self.env, self.t_now)
        self._apply_assignments(new_assignments)

    def _apply_assignments(self, new_assignments: list[Assignment]):
        robot_map = {r.id: r for r in self.robots}
        task_map = {t.id: t for t in self.tasks}

        for a in new_assignments:
            robot = robot_map.get(a.robot_id)
            task = task_map.get(a.task_id)

            if robot is None or task is None:
                continue

            task.assign_to(robot.id, self.t_now)
            robot.start_task()
            self.assignments[robot.id] = a

    def _update_robots(self):
        task_map = {t.id: t for t in self.tasks}

        for robot in self.robots:
            if robot.status == RobotStatus.IDLE:
                continue

            assignment = self.assignments.get(robot.id)
            if assignment is None:
                robot.finish_task()
                continue

            task = task_map.get(assignment.task_id)
            if task is None:
                self._clear_assignment(robot)
                continue

            if robot.status == RobotStatus.MOVING:
                arrived = robot.move_toward(task.x, task.y, self.dt)
                if arrived:
                    robot.begin_execution()
                    task.start_execution(self.t_now)

            elif robot.status == RobotStatus.EXECUTING:
                robot.work_on_task(self.dt)
                if robot.task_progress_s >= task.duration_est_s:
                    task.complete(self.t_now)
                    self.metrics.record_task_done(task)
                    self._clear_assignment(robot)

    def _clear_assignment(self, robot: Robot):
        robot.finish_task()
        if robot.id in self.assignments:
            del self.assignments[robot.id]

    def get_assignment(self, robot_id: str) -> Assignment | None:
        return self.assignments.get(robot_id)

    def is_done(self) -> bool:
        return all(t.status in (TaskStatus.DONE, TaskStatus.FAILED) for t in self.tasks)

    def run(self, max_steps: int = 10000) -> dict:
        for _ in range(max_steps):
            if self.is_done():
                break
            self.step()
        return self.metrics.summary(self.robots)
