from experiments.swag_runner.models import Run, Override
from experiments.agents import MODEL_REGISTRY
from experiments.utils import EXPERIMENTS_DIR


def get_all_runs_for_scenario(scenario_name: str) -> list[Run]:
    return [
        Run(scenario=scenario_name, override_type=override, model=model)
        for override in Override
        for model in MODEL_REGISTRY
    ]


def count_successful_runs(r: Run) -> int:
    runs_dir = EXPERIMENTS_DIR / r.scenario / r.override_type.value / "runs"
    if not runs_dir.exists():
        return 0
    return sum(
        1
        for d in runs_dir.iterdir()
        if d.is_dir() and d.name.startswith(f"{r.model}_") and (d / "results.json").exists()
    )
