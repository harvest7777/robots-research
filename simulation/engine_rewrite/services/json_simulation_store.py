"""
JsonSimulationStore

File-backed implementation of BaseSimulationStore.

Persists robot/task definitions and runtime state to separate JSON files.
The definitions file is written atomically whenever a definition changes and
can be reloaded when the file mtime changes (for external tooling that modifies
it between ticks). The state file is written atomically after every apply(),
allowing external consumers such as an LLM to read a consistent snapshot at
any time.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
from simulation.domain.move_task import MoveTask, MoveTaskState
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.search_task import SearchTask, SearchTaskState
from simulation.domain.task import SpatialConstraint, WorkTask
from simulation.primitives.capability import Capability
from simulation.primitives.position import Position
from simulation.primitives.time import Time
from simulation.primitives.zone import ZoneId

from .base_assignment_service import BaseAssignmentService
from .base_simulation_store import BaseSimulationStore


class JsonSimulationStore(BaseSimulationStore):
    """Persists robot/task definitions and runtime state to JSON files.

    Args:
        registry_path:      Destination file for robot/task definitions.
        state_path:         Destination file for runtime state (written each tick).
        assignment_service: Provides current assignments at state-write time.
        scenario_id:        Written into the state JSON for consumer context.
        max_tick:           Written into the state JSON for consumer context.
    """

    def __init__(
        self,
        registry_path: Path,
        state_path: Path,
        assignment_service: BaseAssignmentService,
        scenario_id: str = "",
        max_tick: int = 0,
    ) -> None:
        self._registry_path = registry_path
        self._state_path = state_path
        self._assignment_service = assignment_service
        self._scenario_id = scenario_id
        self._max_tick = max_tick

        self._cached_mtime: float | None = None
        self._robots: dict[RobotId, Robot] = {}
        self._tasks: dict[TaskId, BaseTask] = {}
        self._robot_states: dict[RobotId, RobotState] = {}
        self._task_states: dict[TaskId, BaseTaskState] = {}

    # ------------------------------------------------------------------
    # Setup API
    # ------------------------------------------------------------------

    def add_robot(self, robot: Robot, state: RobotState) -> None:
        self._reload_if_changed()
        self._robots[robot.id] = robot
        self._robot_states[robot.id] = state
        self._flush_registry()

    def add_task(self, task: BaseTask, state: BaseTaskState) -> None:
        self._reload_if_changed()
        self._tasks[task.id] = task
        self._task_states[task.id] = state
        self._flush_registry()

    # ------------------------------------------------------------------
    # Runner read API
    # ------------------------------------------------------------------

    def all_robots(self) -> list[Robot]:
        self._reload_if_changed()
        return list(self._robots.values())

    def all_tasks(self) -> list[BaseTask]:
        self._reload_if_changed()
        return list(self._tasks.values())

    def get_snapshot(self) -> tuple[dict[RobotId, RobotState], dict[TaskId, BaseTaskState]]:
        return dict(self._robot_states), dict(self._task_states)

    # ------------------------------------------------------------------
    # Runner write API
    # ------------------------------------------------------------------

    def apply(
        self,
        robot_states: dict[RobotId, RobotState],
        task_states: dict[TaskId, BaseTaskState],
    ) -> None:
        self._robot_states = dict(robot_states)
        self._task_states = dict(task_states)
        self._flush_state()

    # ------------------------------------------------------------------
    # Registry IO (definitions file)
    # ------------------------------------------------------------------

    def _reload_if_changed(self) -> None:
        if not self._registry_path.exists():
            return
        mtime = self._registry_path.stat().st_mtime
        if mtime == self._cached_mtime:
            return
        with open(self._registry_path) as f:
            data = json.load(f)
        self._tasks = {t.id: t for t in (_task_from_json(t) for t in data.get("tasks", []))}
        self._robots = {r.id: r for r in (_robot_from_json(r) for r in data.get("robots", []))}
        self._cached_mtime = mtime

    def _flush_registry(self) -> None:
        data = {
            "version": 1,
            "robots": [_robot_to_json(r) for r in self._robots.values()],
            "tasks": [_task_to_json(t) for t in self._tasks.values()],
        }
        _atomic_write(self._registry_path, data)
        self._cached_mtime = (
            self._registry_path.stat().st_mtime if self._registry_path.exists() else None
        )

    # ------------------------------------------------------------------
    # State IO (runtime state file)
    # ------------------------------------------------------------------

    def _flush_state(self) -> None:
        assignments = self._assignment_service.get_current()
        robot_to_task = {a.robot_id: a.task_id for a in assignments}
        task_to_robots: dict[TaskId, list[int]] = {}
        for robot_id, task_id in robot_to_task.items():
            task_to_robots.setdefault(task_id, []).append(int(robot_id))

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
        for task in self._tasks.values():
            task_id = task.id
            ts = self._task_states.get(task_id)
            entry: dict[str, Any] = {
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

        data: dict[str, Any] = {
            "scenario_id": self._scenario_id,
            "max_tick": self._max_tick,
            "robots": robots,
            "tasks": tasks,
            "assignments": [
                {"robot_id": int(a.robot_id), "task_id": int(a.task_id)}
                for a in assignments
            ],
        }
        _atomic_write(self._state_path, data)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _atomic_write(path: Path, data: Any) -> None:
    with tempfile.NamedTemporaryFile("w", dir=path.parent, suffix=".tmp", delete=False) as f:
        json.dump(data, f, indent=2)
        tmp = f.name
    os.replace(tmp, path)


def _capabilities_to_json(caps: frozenset[Capability]) -> list[str]:
    return sorted(c.value for c in caps)


def _capabilities_from_json(values: list[str]) -> frozenset[Capability]:
    return frozenset(Capability(v) for v in values)


def _robot_to_json(robot: Robot) -> dict[str, Any]:
    return {
        "robot_id": int(robot.id),
        "capabilities": _capabilities_to_json(robot.capabilities),
        "speed": robot.speed,
        "battery_drain_per_unit_of_movement": robot.battery_drain_per_unit_of_movement,
        "battery_drain_per_unit_of_work_execution": robot.battery_drain_per_unit_of_work_execution,
        "battery_drain_per_tick_idle": robot.battery_drain_per_tick_idle,
    }


def _robot_from_json(data: dict[str, Any]) -> Robot:
    kwargs: dict[str, Any] = dict(
        id=RobotId(int(data["robot_id"])),
        capabilities=_capabilities_from_json(list(data.get("capabilities", []))),
    )
    if "speed" in data:
        kwargs["speed"] = int(data["speed"])
    if "battery_drain_per_unit_of_movement" in data:
        kwargs["battery_drain_per_unit_of_movement"] = float(data["battery_drain_per_unit_of_movement"])
    if "battery_drain_per_unit_of_work_execution" in data:
        kwargs["battery_drain_per_unit_of_work_execution"] = float(data["battery_drain_per_unit_of_work_execution"])
    if "battery_drain_per_tick_idle" in data:
        kwargs["battery_drain_per_tick_idle"] = float(data["battery_drain_per_tick_idle"])
    return Robot(**kwargs)


def _spatial_constraint_to_json(sc: SpatialConstraint | None) -> dict[str, Any] | None:
    if sc is None:
        return None
    target = sc.target
    if isinstance(target, Position):
        target_json: dict[str, Any] = {"type": "position", "x": target.x, "y": target.y}
    else:
        target_json = {"type": "zone", "zone_id": int(target)}
    return {"target": target_json, "max_distance": sc.max_distance}


def _spatial_constraint_from_json(data: dict[str, Any] | None) -> SpatialConstraint | None:
    if data is None:
        return None
    tgt = data["target"]
    if tgt["type"] == "position":
        target = Position(int(tgt["x"]), int(tgt["y"]))
    elif tgt["type"] == "zone":
        target = ZoneId(int(tgt["zone_id"]))
    else:
        raise ValueError(f"Unknown spatial_constraint.target.type: {tgt['type']}")
    return SpatialConstraint(target=target, max_distance=int(data.get("max_distance", 0)))


def _task_to_json(task: BaseTask) -> dict[str, Any]:
    base: dict[str, Any] = {
        "task_id": int(task.id),
        "priority": task.priority,
        "required_capabilities": _capabilities_to_json(task.required_capabilities),
        "dependencies": [int(t) for t in sorted(task.dependencies)],
    }

    if isinstance(task, SearchTask):
        base["task_type"] = "search"
        return base

    if isinstance(task, MoveTask):
        base["task_type"] = "move"
        base["destination"] = {"x": task.destination.x, "y": task.destination.y}
        base["min_robots_required"] = task.min_robots_required
        base["min_distance"] = task.min_distance
        return base

    if isinstance(task, WorkTask):
        base["task_type"] = "work"
        base["required_work_time"] = task.required_work_time.tick
        base["spatial_constraint"] = _spatial_constraint_to_json(task.spatial_constraint)
        base["deadline"] = task.deadline.tick if task.deadline is not None else None
        base["min_robots_needed"] = task.min_robots_needed
        return base

    raise TypeError(f"Unsupported task type for JSON store: {type(task).__name__}")


def _task_from_json(data: dict[str, Any]) -> BaseTask:
    task_type = data.get("task_type")
    base_kwargs = dict(
        id=TaskId(int(data["task_id"])),
        priority=int(data.get("priority", 0)),
        required_capabilities=_capabilities_from_json(list(data.get("required_capabilities", []))),
        dependencies=frozenset(TaskId(int(t)) for t in data.get("dependencies", [])),
    )

    if task_type == "search":
        return SearchTask(**base_kwargs)

    if task_type == "move":
        dest = data.get("destination") or {}
        return MoveTask(
            **base_kwargs,
            destination=Position(int(dest.get("x", 0)), int(dest.get("y", 0))),
            min_robots_required=int(data.get("min_robots_required", 1)),
            min_distance=int(data.get("min_distance", 1)),
        )

    if task_type == "work":
        deadline = data.get("deadline")
        return WorkTask(
            **base_kwargs,
            required_work_time=Time(int(data.get("required_work_time", 0))),
            spatial_constraint=_spatial_constraint_from_json(data.get("spatial_constraint")),
            deadline=Time(int(deadline)) if deadline is not None else None,
            min_robots_needed=int(data.get("min_robots_needed", 1)),
        )

    raise ValueError(f"Unknown task_type in JSON store: {task_type!r}")
