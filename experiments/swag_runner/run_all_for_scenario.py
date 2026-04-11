from experiments.swag_runner.models import Run, Override
from experiments.utils import EXPERIMENTS_DIR
from experiments.agents import MODEL_REGISTRY
from experiments.swag_runner.run import run
from experiments.swag_runner.run_all import count_successful_runs, DESIRED_RUNS_PER_EXPERIMENT

import argparse


def _get_all_runs_for_scenario(scenario_name: str) -> list[Run]:
    return [
        Run(scenario=scenario_name, override_type=override, model=model)
        for override in Override
        for model in MODEL_REGISTRY
    ]


def run_all_for_scenario(scenario_name: str) -> None:
    all_runs = _get_all_runs_for_scenario(scenario_name)
    fail_cache = {}

    for r in all_runs:
        current = count_successful_runs(r)
        if current >= DESIRED_RUNS_PER_EXPERIMENT:
            print(f"skip {r.scenario}/{r.override_type.value}/{r.model} ({current} runs already)")
            continue
        needed = DESIRED_RUNS_PER_EXPERIMENT - current
        for i in range(needed):
            print(f"running {r.scenario}/{r.override_type.value}/{r.model} (run {current + i + 1}/{DESIRED_RUNS_PER_EXPERIMENT})")
            if r.model in fail_cache:
                print(f"   FAILED: cached failure")
                continue
            try:
                run(r)
            except Exception as e:
                fail_cache[r.model] = e
                print(f"  FAILED: {str(e)[:100]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", type=str)
    args = parser.parse_args()
    run_all_for_scenario(args.scenario)
