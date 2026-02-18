from __future__ import annotations

import argparse
import os
import time

from scenario_loaders import load_simulation
from coordinator_algorithms import simple_assign
from pathfinding_algorithms import bfs_pathfind
from simulation_view.simulation_view import SimulationView
from simulation_view.terminal_renderer import TerminalRenderer

NUM_TICKS = 60


def main() -> None:
    parser = argparse.ArgumentParser(description="Load and run a simulation scenario")
    parser.add_argument("scenario", help="Path to the scenario JSON file")
    parser.add_argument(
        "--renderer",
        choices=["terminal", "mujoco"],
        default="terminal",
        help="Renderer to use (default: terminal)",
    )
    args = parser.parse_args()

    sim = load_simulation(args.scenario)
    sim.assignment_algorithm = simple_assign
    sim.pathfinding_algorithm = bfs_pathfind

    if args.renderer == "mujoco":
        from simulation_view.mujoco_renderer import MuJoCoRenderer

        renderer = MuJoCoRenderer()
        try:
            renderer.update(sim.snapshot())
            for _ in range(NUM_TICKS):
                time.sleep(0.3)
                sim.step()
                renderer.update(sim.snapshot())
            renderer.wait_for_close()
        finally:
            renderer.cleanup()
    else:
        renderer = TerminalRenderer()
        try:
            cols, rows = os.get_terminal_size()
            frame = SimulationView(sim.snapshot()).render(cols, rows)
            renderer.draw(frame)

            for _ in range(NUM_TICKS):
                time.sleep(1)
                sim.step()
                cols, rows = os.get_terminal_size()
                frame = SimulationView(sim.snapshot()).render(cols, rows)
                renderer.draw(frame)
        finally:
            renderer.cleanup()


if __name__ == "__main__":
    main()
