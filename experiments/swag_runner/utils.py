from pathlib import Path
from experiments.swag_runner.models import Run, Override

EXPERIMENTS_DIR = Path(__file__).parent.parent

def count_successful_runs(run: Run) -> int:
    runs_dir = EXPERIMENTS_DIR / run.scenario / run.override_type.value / "runs"
    if not runs_dir.exists():
        return 0
    return sum(
        1
        for d in runs_dir.iterdir()
        if d.is_dir() and d.name.startswith(f"{run.model}_") and (d / "results.json").exists()
    )

print(count_successful_runs(Run("scenario_05", Override.BASELINE, "asi1")))