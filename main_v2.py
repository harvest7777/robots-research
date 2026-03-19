"""
main_v2.py — entry point for the new simulation engine.

Runs a scenarios_v2 scenario with file-backed assignment and state services
so the MCP server can observe state and inject assignments in real time.

  State is written to:      sim_state_v2.json
  Assignments are read from: sim_assignments_v2.json

Usage:
    python main_v2.py [scenario] [--max-ticks N] [--delay S]

    scenario: module name under scenarios_v2/ (default: search_and_rescue_move)
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from importlib import import_module
from pathlib import Path

from simulation.domain import MoveTask, MoveTaskState, RescuePoint, SearchTask, SearchTaskState
from simulation.engine_rewrite import SimulationState
from simulation.engine_rewrite.services import JsonAssignmentService
from simulation_view.terminal_renderer import TerminalRenderer
from simulation_view.v2.view import SimulationViewV2

_ROOT = Path(__file__).parent
_STATE_PATH = _ROOT / "sim_state_v2.json"
_ASSIGNMENTS_PATH = _ROOT / "sim_assignments_v2.json"

_DEFAULT_MAX_TICKS = 500


def _write_state(state: SimulationState, scenario_id: str, max_tick: int) -> None:
    """Serialize SimulationState to sim_state_v2.json atomically."""
    robot_to_task = {a.robot_id: a.task_id for a in state.assignments}
    task_to_robots: dict = {}
    for robot_id, task_id in robot_to_task.items():
        task_to_robots.setdefault(task_id, []).append(robot_id)

    robots = [
        {
            "robot_id": rs.robot_id,
            "x": rs.position.x,
            "y": rs.position.y,
            "battery_level": rs.battery_level,
        }
        for rs in state.robot_states.values()
    ]

    tasks = []
    for task_id, task in state.tasks.items():
        ts = state.task_states.get(task_id)
        entry: dict = {
            "task_id": task_id,
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
        elif isinstance(task, RescuePoint):
            entry["task_type"] = "rescue_point"
            entry["location"] = [task.position.x, task.position.y]
        elif isinstance(task, SearchTask):
            entry["task_type"] = "search"
            if isinstance(ts, SearchTaskState):
                entry["rescue_found"] = sorted(ts.rescue_found)
        else:
            entry["task_type"] = "work"
        tasks.append(entry)

    data = {
        "scenario_id": scenario_id,
        "current_tick": state.t_now.tick,
        "max_tick": max_tick,
        "robots": robots,
        "tasks": tasks,
        "assignments": [
            {"robot_id": a.robot_id, "task_id": a.task_id}
            for a in state.assignments
        ],
    }
    dir_ = _STATE_PATH.parent
    with tempfile.NamedTemporaryFile("w", dir=dir_, suffix=".tmp", delete=False) as f:
        json.dump(data, f, indent=2)
        tmp = f.name
    os.replace(tmp, _STATE_PATH)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a scenarios_v2 simulation with MCP support"
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default="search_and_rescue_move",
        help="Module name under scenarios_v2/ (default: search_and_rescue_move)",
    )
    parser.add_argument("--max-ticks", type=int, default=_DEFAULT_MAX_TICKS)
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Seconds to sleep between ticks (default: 0.1)",
    )
    args = parser.parse_args()

    mod = import_module(f"scenarios_v2.{args.scenario}")
    json_svc = JsonAssignmentService(_ASSIGNMENTS_PATH)
    runner, _ = mod.build(assignment_service=json_svc)

    view = SimulationViewV2()
    renderer = TerminalRenderer()

    try:
        for _ in range(args.max_ticks):
            state, _ = runner.step()
            _write_state(state, args.scenario, args.max_ticks)

            cols, rows = os.get_terminal_size()
            frame = view.render(state, width=cols, height=rows)
            renderer.draw(frame)

            time.sleep(args.delay)
    finally:
        renderer.cleanup()


if __name__ == "__main__":
    main()
