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
import os
import time
from importlib import import_module
from pathlib import Path

from simulation.engine_rewrite.services import JsonAssignmentService, JsonSimulationStateService
from simulation_view.terminal_renderer import TerminalRenderer
from simulation_view.v2.view import SimulationViewV2

_ROOT = Path(__file__).parent
_STATE_PATH = _ROOT / "sim_state_v2.json"
_ASSIGNMENTS_PATH = _ROOT / "sim_assignments_v2.json"

_DEFAULT_MAX_TICKS = 500


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

    json_assignment_svc = JsonAssignmentService(_ASSIGNMENTS_PATH)
    runner, _ = import_module(f"scenarios_v2.{args.scenario}").build(
        assignment_service=json_assignment_svc
    )

    # Hot-swap the in-memory state service for a file-backed one so external
    # consumers (e.g. an LLM on a separate thread) can read state between ticks.
    json_state_svc = JsonSimulationStateService(
        path=_STATE_PATH,
        registry=runner.registry,
        assignment_service=json_assignment_svc,
        scenario_id=args.scenario,
        max_tick=args.max_ticks,
    )
    runner.use_state_service(json_state_svc)

    view = SimulationViewV2()
    renderer = TerminalRenderer()

    try:
        for _ in range(args.max_ticks):
            state, _ = runner.step()

            cols, rows = os.get_terminal_size()
            frame = view.render(state, width=cols, height=rows)
            renderer.draw(frame)

            time.sleep(args.delay)
    finally:
        renderer.cleanup()


if __name__ == "__main__":
    main()
