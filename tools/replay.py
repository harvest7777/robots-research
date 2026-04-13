"""
tools/replay.py

Replay a simulation from a simulation_replay.json artifact using the terminal view.

Usage:
    python tools/replay.py <path/to/simulation_replay.json> [--delay 0.1] [--step]

Options:
    --delay SECONDS   Seconds between frames (default: 0.1). Ignored if --step is set.
    --step            Advance one frame per Enter keypress.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from simulation.domain.assignment import Assignment
from simulation.domain.environment import Environment
from simulation.domain.move_task import MoveTask, MoveTaskState
from simulation.domain.rescue_point import RescuePoint
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.search_task import SearchTask, SearchTaskState
from simulation.domain.simulation_state import SimulationState
from simulation.domain.task import SpatialConstraint, WorkTask
from simulation.domain.task_state import TaskState
from simulation.domain.base_task import TaskId, TaskStatus
from simulation.primitives.capability import Capability
from simulation.primitives.position import Position
from simulation.primitives.time import Time
from simulation.primitives.zone import Zone, ZoneId, ZoneType
from simulation_view.base_simulation_view import BaseViewService
from simulation_view.terminal.terminal_view_service import TerminalViewService


# ---------------------------------------------------------------------------
# Deserializers
# ---------------------------------------------------------------------------

def _pos(d: dict) -> Position:
    return Position(d["x"], d["y"])


def _spatial_constraint(d: dict) -> SpatialConstraint:
    if d["target_type"] == "position":
        target = _pos(d["target"])
    else:
        target = ZoneId(d["target"])
    return SpatialConstraint(target=target, max_distance=d["max_distance"])


def _task(d: dict) -> WorkTask | SearchTask | MoveTask:
    caps = frozenset(Capability(c) for c in d["required_capabilities"])
    t = d["type"]
    if t == "work_task":
        return WorkTask(
            id=TaskId(d["id"]),
            priority=d["priority"],
            required_capabilities=caps,
            required_work_time=Time(d["required_work_time"]),
            spatial_constraint=_spatial_constraint(d["spatial_constraint"]) if d["spatial_constraint"] else None,
            deadline=Time(d["deadline"]) if d["deadline"] is not None else None,
            min_robots_needed=d["min_robots_needed"],
        )
    if t == "search_task":
        return SearchTask(id=TaskId(d["id"]), priority=d["priority"], required_capabilities=caps)
    if t == "move_task":
        return MoveTask(
            id=TaskId(d["id"]),
            priority=d["priority"],
            required_capabilities=caps,
            destination=_pos(d["destination"]),
            min_robots_required=d["min_robots_required"],
            min_distance=d["min_distance"],
        )
    raise ValueError(f"Unknown task type: {t}")


def _task_state(d: dict) -> TaskState | SearchTaskState | MoveTaskState:
    status = TaskStatus(d["status"]) if d["status"] else None
    completed_at = Time(d["completed_at"]) if d["completed_at"] is not None else None
    t = d["type"]
    if t == "task_state":
        return TaskState(
            task_id=TaskId(d["task_id"]),
            status=status,
            completed_at=completed_at,
            work_done=Time(d["work_done"]),
            started_at=Time(d["started_at"]) if d["started_at"] is not None else None,
        )
    if t == "search_task_state":
        return SearchTaskState(
            task_id=TaskId(d["task_id"]),
            status=status,
            completed_at=completed_at,
            rescue_found=frozenset(TaskId(x) for x in d["rescue_found"]),
        )
    if t == "move_task_state":
        return MoveTaskState(
            task_id=TaskId(d["task_id"]),
            status=status,
            completed_at=completed_at,
            current_position=_pos(d["current_position"]),
        )
    raise ValueError(f"Unknown task state type: {t}")


def _robot(d: dict) -> Robot:
    return Robot(
        id=RobotId(d["id"]),
        capabilities=frozenset(Capability(c) for c in d["capabilities"]),
        speed=d["speed"],
        battery_drain_per_unit_of_movement=d["battery_drain_per_unit_of_movement"],
        battery_drain_per_unit_of_work_execution=d["battery_drain_per_unit_of_work_execution"],
        battery_drain_per_tick_idle=d["battery_drain_per_tick_idle"],
    )


def _robot_state(d: dict) -> RobotState:
    return RobotState(
        robot_id=RobotId(d["robot_id"]),
        position=_pos(d["position"]),
        battery_level=d["battery_level"],
        current_waypoint=_pos(d["current_waypoint"]) if d["current_waypoint"] else None,
    )


def _rescue_point(d: dict) -> RescuePoint:
    return RescuePoint(
        id=TaskId(d["id"]),
        name=d["name"],
        spatial_constraint=_spatial_constraint(d["spatial_constraint"]),
        task=_task(d["task"]),
        initial_task_state=_task_state(d["initial_task_state"]),
    )


def _environment(d: dict) -> Environment:
    env = Environment(width=d["width"], height=d["height"])
    for obs in d["obstacles"]:
        env.add_obstacle(_pos(obs))
    for zone_d in d["zones"].values():
        env.add_zone(Zone.from_positions(
            id=ZoneId(zone_d["id"]),
            zone_type=ZoneType(zone_d["zone_type"]),
            positions=[_pos(p) for p in zone_d["cells"]],
        ))
    for rp_d in d["rescue_points"].values():
        env.add_rescue_point(_rescue_point(rp_d))
    return env


def _state(d: dict) -> SimulationState:
    return SimulationState(
        environment=_environment(d["environment"]),
        robots={RobotId(int(k)): _robot(v) for k, v in d["robots"].items()},
        robot_states={RobotId(int(k)): _robot_state(v) for k, v in d["robot_states"].items()},
        tasks={TaskId(int(k)): _task(v) for k, v in d["tasks"].items()},
        task_states={TaskId(int(k)): _task_state(v) for k, v in d["task_states"].items()},
        assignments=tuple(
            Assignment(robot_id=RobotId(a["robot_id"]), task_id=TaskId(a["task_id"]))
            for a in d["assignments"]
        ),
        t_now=Time(d["t_now"]),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _make_view(viewer: str) -> BaseViewService:
    if viewer == "mujoco":
        from simulation_view.mujoco.mujoco_view_service import MujocoViewService
        return MujocoViewService()
    return TerminalViewService()


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a simulation in the terminal.")
    parser.add_argument("replay", type=Path, help="Path to simulation_replay.json")
    parser.add_argument("--viewer", choices=["terminal", "mujoco"], default="terminal",
                        help="Viewer to use (default: terminal)")
    parser.add_argument("--delay", type=float, default=0.1, help="Seconds between frames (default: 0.1)")
    parser.add_argument("--step", action="store_true", help="Press Enter to advance each frame")
    args = parser.parse_args()

    frames = json.loads(args.replay.read_text())
    view = _make_view(args.viewer)

    try:
        for frame in frames:
            if not view.is_running():
                break
            view.render(_state(frame["state"]))
            if args.step:
                input()
            else:
                time.sleep(args.delay)
    finally:
        view.handle_exit()


if __name__ == "__main__":
    main()
