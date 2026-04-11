from experiments.swag_runner.models import Run
from experiments.utils import EXPERIMENTS_DIR


def count_successful_runs(r: Run) -> int:
    runs_dir = EXPERIMENTS_DIR / r.scenario / r.override_type.value / "runs"
    if not runs_dir.exists():
        return 0
    return sum(
        1
        for d in runs_dir.iterdir()
        if d.is_dir() and d.name.startswith(f"{r.model}_") and (d / "results.json").exists()
    )
