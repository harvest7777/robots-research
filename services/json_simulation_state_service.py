"""
JsonSimulationStateService: file-backed implementation of BaseSimulationStateService.

Writes state atomically (via a temp file + rename) so MCP reads never see
a partial write. On simulation start, call write() with the initial state to
reset the file for a fresh run.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from services.base_simulation_state_service import (
    BaseSimulationStateService,
    RobotStateSnapshot,
    SimulationState,
    TaskStateSnapshot,
)
from simulation.domain.robot_state import RobotId
from simulation.domain.task import TaskId
from simulation.domain.task_state import TaskStatus
from simulation.primitives.time import Time


class JsonSimulationStateService(BaseSimulationStateService):
    def __init__(self, path: Path) -> None:
        self._path = path

    def write(self, state: SimulationState) -> None:
        data = {
            "scenario_id": state.scenario_id,
            "current_tick": state.current_tick,
            "max_tick": state.max_tick,
            "robots": [
                {
                    "robot_id": r.robot_id,
                    "x": r.x,
                    "y": r.y,
                    "battery_level": r.battery_level,
                    "current_waypoint": list(r.current_waypoint) if r.current_waypoint is not None else None,
                }
                for r in state.robots
            ],
            "tasks": [
                {
                    "task_id": t.task_id,
                    "status": t.status.value,
                    "work_done_ticks": t.work_done_ticks,
                    "assigned_robot_ids": list(t.assigned_robot_ids),
                }
                for t in state.tasks
            ],
        }
        dir_ = self._path.parent
        with tempfile.NamedTemporaryFile(
            "w", dir=dir_, suffix=".tmp", delete=False
        ) as f:
            json.dump(data, f, indent=2)
            tmp_path = f.name
        os.replace(tmp_path, self._path)

    def read(self) -> SimulationState | None:
        if not self._path.exists():
            return None
        with open(self._path) as f:
            data = json.load(f)
        robots = [
            RobotStateSnapshot(
                robot_id=RobotId(r["robot_id"]),
                x=r["x"],
                y=r["y"],
                battery_level=r["battery_level"],
                current_waypoint=tuple(r["current_waypoint"]) if r.get("current_waypoint") is not None else None,
            )
            for r in data["robots"]
        ]
        tasks = [
            TaskStateSnapshot(
                task_id=TaskId(t["task_id"]),
                status=TaskStatus(t["status"]),
                work_done_ticks=t["work_done_ticks"],
                assigned_robot_ids=[RobotId(rid) for rid in t["assigned_robot_ids"]],
            )
            for t in data["tasks"]
        ]
        return SimulationState(
            scenario_id=data["scenario_id"],
            current_tick=data["current_tick"],
            max_tick=data["max_tick"],
            robots=robots,
            tasks=tasks,
        )

    def update_current_tick(self, tick: int) -> None:
        if not self._path.exists():
            return
        with open(self._path) as f:
            data = json.load(f)
        data["current_tick"] = tick
        dir_ = self._path.parent
        with tempfile.NamedTemporaryFile(
            "w", dir=dir_, suffix=".tmp", delete=False
        ) as f:
            json.dump(data, f, indent=2)
            tmp_path = f.name
        os.replace(tmp_path, self._path)
