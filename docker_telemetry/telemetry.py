from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from simulation.primitives.capability import Capability
from simulation.primitives.position import Position
from simulation.primitives.time import Time
from simulation.domain.robot_state import RobotId
from simulation.domain.base_task import TaskId
from simulation.domain.step_outcome import IgnoreReason


class RobotAction(Enum):
    MOVED  = "moved"   # robot appears in outcome.moved
    WORKED = "worked"  # robot appears in outcome.worked
    STUCK  = "stuck"   # robot appears in outcome.robots_stuck
    IDLE   = "idle"    # robot appears in none of the above


@dataclass(frozen=True)
class RobotTelemetry:
    tick:                 Time
    robot_id:             RobotId
    position:             Position
    battery_level:        float
    current_waypoint:     Position | None
    action:               RobotAction
    assigned_task_ids:    tuple[TaskId, ...]
    task_capabilities:    frozenset[Capability]
    task_complexity:      int | None
    deadline_delta_ticks: int | None
    ignore_reasons:       tuple[IgnoreReason, ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "tick":                 self.tick.tick,
            "robot_id":             int(self.robot_id),
            "position":             {"x": self.position.x, "y": self.position.y},
            "battery_level":        self.battery_level,
            "current_waypoint":     (
                {"x": self.current_waypoint.x, "y": self.current_waypoint.y}
                if self.current_waypoint is not None else None
            ),
            "action":               self.action.value,
            "assigned_task_ids":    [int(t) for t in self.assigned_task_ids],
            "task_capabilities":    sorted(c.value for c in self.task_capabilities),
            "task_complexity":      self.task_complexity,
            "deadline_delta_ticks": self.deadline_delta_ticks,
            "ignore_reasons":       [r.value for r in self.ignore_reasons],
        }
