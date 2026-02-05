from __future__ import annotations

import argparse

from scenario_loaders import load_simulation
from coordinator_algorithms import simple_assign 


def main() -> None:
    parser = argparse.ArgumentParser(description="Load and run a simulation scenario")
    parser.add_argument("scenario", help="Path to the scenario JSON file")
    args = parser.parse_args()

    sim = load_simulation(args.scenario)
    sim.assignment_algorithm = simple_assign
    sim.step()


if __name__ == "__main__":
    main()
