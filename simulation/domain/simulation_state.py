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
            "robots": {
                str(rid): {
                    "position": {"x": rs.position.x, "y": rs.position.y},
                    "battery": rs.battery_level,
                }
                for rid, rs in self.robot_states.items()
            },
            "tasks": {
                str(tid): {
                    "status": ts.status.value if ts.status else None,
                }
                for tid, ts in self.task_states.items()
            },
            "assignments": [
                {"robot_id": int(a.robot_id), "task_id": int(a.task_id)}
                for a in self.assignments
            ],
        }

    def to_json_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "t_now": self.t_now.tick,
            "robots": {
                str(rid): {
                    "position": {"x": rs.position.x, "y": rs.position.y},
                    "battery": rs.battery_level,
                }
                for rid, rs in self.robot_states.items()
            },
            "tasks": {
                str(tid): {
                    "status": ts.status.value if ts.status else None,
                }
                for tid, ts in self.task_states.items()
            },
            "assignments": [
                {"robot_id": int(a.robot_id), "task_id": int(a.task_id)}
                for a in self.assignments
            ],
        }
