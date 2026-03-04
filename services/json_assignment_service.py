"""
JsonAssignmentService: file-backed implementation of BaseAssignmentService.

Writes atomically (temp file + rename). Reads on every call so the simulation
always picks up assignments written by the MCP server mid-run.

Fresh-run behaviour: call set_assignments() at simulation start to overwrite
the file with the initial seed — clearing any state from the previous run.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from services.base_assignment_service import BaseAssignmentService
from simulation_models.assignment import Assignment, RobotId
from simulation_models.task import TaskId
from simulation_models.time import Time


class JsonAssignmentService(BaseAssignmentService):
    def __init__(self, path: Path) -> None:
        self._path = path

    # ------------------------------------------------------------------
    # BaseAssignmentService interface
    # ------------------------------------------------------------------

    def get_assignments_for_time(self, time: Time) -> list[Assignment]:
        assignments = self._load()
        all_robot_ids: set[RobotId] = {
            rid for a in assignments for rid in a.robot_ids
        }
        seen: set[Assignment] = set()
        for robot_id in all_robot_ids:
            applicable = [
                a for a in assignments
                if robot_id in a.robot_ids and a.assign_at.tick <= time.tick
            ]
            if applicable:
                seen.add(max(applicable, key=lambda a: a.assign_at.tick))
        return list(seen)

    def set_assignments(self, assignments: list[Assignment]) -> None:
        self._save(assignments)

    def add_assignments(self, assignments: list[Assignment]) -> None:
        existing = self._load()
        self._save(existing + assignments)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> list[Assignment]:
        if not self._path.exists():
            return []
        with open(self._path) as f:
            data = json.load(f)
        return [
            Assignment(
                task_id=TaskId(a["task_id"]),
                robot_ids=frozenset(RobotId(rid) for rid in a["robot_ids"]),
                assign_at=Time(a["assign_at"]),
            )
            for a in data["assignments"]
        ]

    def _save(self, assignments: list[Assignment]) -> None:
        data = {
            "assignments": [
                {
                    "task_id": a.task_id,
                    "robot_ids": list(a.robot_ids),
                    "assign_at": a.assign_at.tick,
                }
                for a in assignments
            ]
        }
        dir_ = self._path.parent
        with tempfile.NamedTemporaryFile(
            "w", dir=dir_, suffix=".tmp", delete=False
        ) as f:
            json.dump(data, f, indent=2)
            tmp_path = f.name
        os.replace(tmp_path, self._path)
