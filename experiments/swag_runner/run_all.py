from experiments.swag_runner.models import Run, Override
from experiments.utils import EXPERIMENTS_DIR
from experiments.agents import MODEL_REGISTRY
from experiments.swag_runner.run import run

DESIRED_RUNS_PER_EXPERIMENT = 1


def count_successful_runs(r: Run) -> int:
    runs_dir = EXPERIMENTS_DIR / r.scenario / r.override_type.value / "runs"
    if not runs_dir.exists():
        return 0
    return sum(
        1
        for d in runs_dir.iterdir()
        if d.is_dir() and d.name.startswith(f"{r.model}_") and (d / "results.json").exists()
    )


def _get_all_runs() -> list[Run]:
    scenarios = sorted(d.name for d in EXPERIMENTS_DIR.iterdir() if d.is_dir() and d.name.startswith("scenario_"))
    return [
        Run(scenario=scenario, override_type=override, model=model)
        for scenario in scenarios
        for override in Override
        for model in MODEL_REGISTRY
    ]


def run_all() -> None:
    all_runs = _get_all_runs()
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
    run_all()
