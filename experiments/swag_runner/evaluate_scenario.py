from experiments.swag_runner.models import Override
from experiments.swag_runner.utils import count_successful_runs, get_all_runs_for_scenario

import argparse

DESIRED_RUN_COUNT = 1


def evaluate_scenario(scenario_name: str) -> None:
    all_runs = get_all_runs_for_scenario(scenario_name)

    for override in Override:
        runs = [r for r in all_runs if r.override_type == override]
        succeeded = []
        failed = []

        for r in runs:
            if count_successful_runs(r) >= DESIRED_RUN_COUNT:
                succeeded.append(r.model)
            else:
                failed.append(r.model)

        print(f"\n[{scenario_name} / {override.value}]")
        print(f"  succeeded ({len(succeeded)}): {', '.join(succeeded) if succeeded else 'none'}")
        print(f"  failed    ({len(failed)}): {', '.join(failed) if failed else 'none'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", type=str)
    args = parser.parse_args()
    evaluate_scenario(args.scenario)
