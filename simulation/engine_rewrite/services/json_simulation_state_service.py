"""
JsonSimulationStateService

File-backed implementation of BaseSimulationStateService.

On every apply() call, serializes the current simulation state to JSON
atomically (temp file + rename) so external consumers — such as an LLM
running on a separate thread — always see a complete, consistent snapshot.

The output format is the same as the legacy _write_state() helper in
main_v2.py, which this class replaces.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from simulation.domain.base_task import BaseTaskState, TaskId
from simulation.domain.move_task import MoveTask, MoveTaskState
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.search_task import SearchTask, SearchTaskState

from .base_assignment_service import BaseAssignmentService
from .base_simulation_registry import BaseSimulationRegistry
from .base_simulation_state_service import BaseSimulationStateService


class JsonSimulationStateService(BaseSimulationStateService):
    """Persists robot/task state to a JSON file after each tick.

    Args:
        path:               Destination file (written atomically).
        registry:           Provides task definitions at write time.
        assignment_service: Provides current assignments at write time.
        scenario_id:        Written into the JSON for consumer context.
        max_tick:           Written into the JSON for consumer context.
    """

    def __init__(
        self,
        path: Path,
        registry: BaseSimulationRegistry,
        assignment_service: BaseAssignmentService,
        scenario_id: str = "",
        max_tick: int = 0,
    ) -> None:
        self._path = path
        self._registry = registry
        self._assignment_service = assignment_service
        self._scenario_id = scenario_id
        self._max_tick = max_tick
        self._robot_states: dict[RobotId, RobotState] = {}
        self._task_states: dict[TaskId, BaseTaskState] = {}

    # ------------------------------------------------------------------
    # BaseSimulationStateService
    # ------------------------------------------------------------------

    def get_snapshot(self) -> tuple[dict[RobotId, RobotState], dict[TaskId, BaseTaskState]]:
        return dict(self._robot_states), dict(self._task_states)

    def apply(
        self,
        robot_states: dict[RobotId, RobotState],
        task_states: dict[TaskId, BaseTaskState],
    ) -> None:
        self._robot_states = dict(robot_states)
        self._task_states = dict(task_states)
        self._flush()

    def init_robot(self, robot_id: RobotId, state: RobotState) -> None:
        self._robot_states[robot_id] = state

    def init_task(self, task_id: TaskId, state: BaseTaskState) -> None:
        self._task_states[task_id] = state

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def _flush(self) -> None:
        assignments = self._assignment_service.get_current()
        robot_to_task = {a.robot_id: a.task_id for a in assignments}
        task_to_robots: dict[TaskId, list[int]] = {}
        for robot_id, task_id in robot_to_task.items():
            task_to_robots.setdefault(task_id, []).append(int(robot_id))

        # Determine the current tick from any robot state (t_now is not stored
        # separately, but robot states are stamped by the engine indirectly;
        # we derive it from the number of applied() calls instead).
        # We leave it to callers to set tick via the scenario_id/max_tick metadata.

        robots = [
            {
                "robot_id": int(rs.robot_id),
                "x": rs.position.x,
                "y": rs.position.y,
                "battery_level": rs.battery_level,
            }
            for rs in self._robot_states.values()
        ]

        tasks = []
        for task in self._registry.all_tasks():
            task_id = task.id
            ts = self._task_states.get(task_id)
            entry: dict = {
                "task_id": int(task_id),
                "priority": task.priority,
                "status": ts.status.value if ts and ts.status else None,
                "assigned_robot_ids": sorted(task_to_robots.get(task_id, [])),
            }
            if isinstance(task, MoveTask):
                entry["task_type"] = "move"
                entry["destination"] = [task.destination.x, task.destination.y]
                entry["min_robots_required"] = task.min_robots_required
                if isinstance(ts, MoveTaskState):
                    entry["current_position"] = [ts.current_position.x, ts.current_position.y]
            elif isinstance(task, SearchTask):
                entry["task_type"] = "search"
                if isinstance(ts, SearchTaskState):
                    entry["rescue_found"] = sorted(int(r) for r in ts.rescue_found)
            else:
                entry["task_type"] = "work"
            tasks.append(entry)

        data = {
            "scenario_id": self._scenario_id,
            "max_tick": self._max_tick,
            "robots": robots,
            "tasks": tasks,
            "assignments": [
                {"robot_id": int(a.robot_id), "task_id": int(a.task_id)}
                for a in assignments
            ],
        }
        dir_ = self._path.parent
        with tempfile.NamedTemporaryFile("w", dir=dir_, suffix=".tmp", delete=False) as f:
            json.dump(data, f, indent=2)
            tmp = f.name
        os.replace(tmp, self._path)
