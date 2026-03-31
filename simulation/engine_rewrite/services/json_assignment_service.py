"""
JsonAssignmentService

File-backed implementation of BaseAssignmentService for the new engine.

Writes atomically (temp file + rename) so concurrent readers never see a
partial write. Maintains one assignment per robot — same contract as
InMemoryAssignmentService.

Used by main.py so the MCP server can inject assignments by writing to
the JSON file while the simulation is running.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from simulation.domain import TaskId, RobotId, Assignment

from .base_assignment_service import BaseAssignmentService


class JsonAssignmentService(BaseAssignmentService):

    def __init__(self, path: Path, initial: list[Assignment] | None = None) -> None:
        self._path = path
        self._cached_mtime: float | None = None
        self._cached: list[Assignment] = []
        if initial is not None:
            self._flush({a.robot_id: a for a in initial})

    def get_current(self) -> list[Assignment]:
        if not self._path.exists():
            return []
        mtime = self._path.stat().st_mtime
        if mtime == self._cached_mtime:
            return list(self._cached)
        with open(self._path) as f:
            data = json.load(f)
        self._cached = [
            Assignment(task_id=TaskId(a["task_id"]), robot_id=RobotId(a["robot_id"]))
            for a in data
        ]
        self._cached_mtime = mtime
        return list(self._cached)

    def update(self, assignments: list[Assignment]) -> None:
        current = {a.robot_id: a for a in self.get_current()}
        for a in assignments:
            current[a.robot_id] = a
        self._flush(current)

    def unassign(self, robot_id: RobotId) -> None:
        current = {a.robot_id: a for a in self.get_current()}
        current.pop(robot_id, None)
        self._flush(current)

    def clear(self) -> None:
        """Remove all assignments — robots will idle."""
        self._flush({})

    def _flush(self, by_robot: dict[RobotId, Assignment]) -> None:
        data = [
            {"robot_id": a.robot_id, "task_id": a.task_id}
            for a in by_robot.values()
        ]
        dir_ = self._path.parent
        with tempfile.NamedTemporaryFile("w", dir=dir_, suffix=".tmp", delete=False) as f:
            json.dump(data, f)
            tmp = f.name
        os.replace(tmp, self._path)
