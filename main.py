from __future__ import annotations

import argparse
import os
import time

from scenario_loaders import load_simulation
from coordinator_algorithms import simple_assign
from pathfinding_algorithms import bfs_pathfind
from simulation_view.simulation_view import SimulationView

NUM_TICKS = 15


def main() -> None:
    parser = argparse.ArgumentParser(description="Load and run a simulation scenario")
    parser.add_argument("scenario", help="Path to the scenario JSON file")
    args = parser.parse_args()

    sim = load_simulation(args.scenario)
    sim.assignment_algorithm = simple_assign
    sim.pathfinding_algorithm = bfs_pathfind

    os.system("clear")
    print(SimulationView(sim.snapshot()).render())
    for _ in range(NUM_TICKS):
        time.sleep(1)
        sim.step()
        os.system("clear")
        print(SimulationView(sim.snapshot()).render())


if __name__ == "__main__":
    main()
