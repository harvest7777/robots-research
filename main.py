import argparse

from scenario_loaders import load_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Load and run a simulation scenario")
    parser.add_argument("scenario", help="Path to the scenario JSON file")
    args = parser.parse_args()

    sim = load_simulation(args.scenario)
    env = sim["environment"]
    print(f"Loaded environment: {env.width}x{env.height}")
    print(env)


if __name__ == "__main__":
    main()
