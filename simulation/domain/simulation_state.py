"""
SimulationState

Immutable snapshot of all simulation data for one tick.
Passed into classify_step and apply_outcome — never mutated in place.
apply_outcome returns a new SimulationState each tick.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from simulation.domain.assignment import Assignment
from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
from simulation.domain.environment import Environment
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.primitives.time import Time


@dataclass(frozen=True)
class SimulationState:
    environment: Environment
    robots: dict[RobotId, Robot]
    robot_states: dict[RobotId, RobotState]
    tasks: dict[TaskId, BaseTask]
    task_states: dict[TaskId, BaseTaskState]
    t_now: Time = field(default_factory=lambda: Time(0))
    assignments: tuple[Assignment, ...] = ()

    def to_json_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "t_now": self.t_now.tick,
            "environment": self.environment.to_json_dict(),
            "robots": {str(rid): r.to_json_dict() for rid, r in self.robots.items()},
            "robot_states": {str(rid): rs.to_json_dict() for rid, rs in self.robot_states.items()},
            "tasks": {str(tid): t.to_json_dict() for tid, t in self.tasks.items()},
            "task_states": {str(tid): ts.to_json_dict() for tid, ts in self.task_states.items()},
            "assignments": [a.to_json_dict() for a in self.assignments],
        }
