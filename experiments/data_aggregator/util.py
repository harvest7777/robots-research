"""
experiments/data_aggregator/util.py

Shared utilities for loading experiment results.
"""

import json
from pathlib import Path

EXPERIMENTS_DIR = Path(__file__).parent.parent


def collect_results(scenario: str) -> list[dict]:
    results = []
    for results_path in sorted((EXPERIMENTS_DIR / scenario).glob("*/runs/*/results.json")):
        data = json.loads(results_path.read_text())
        if "metadata" not in data:
            print(f"  skipping {results_path} (no metadata)")
            continue
        results.append(data)
    return results
