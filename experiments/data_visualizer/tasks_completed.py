"""
experiments/data_visualizer/tasks_completed.py

Visualizes tasks completed per run, comparing baseline vs structured_override.

Usage (from repo root):
    python -m experiments.data_visualizer.tasks_completed --scenario scenario_05
    python -m experiments.data_visualizer.tasks_completed --scenario scenario_05 --out my_chart.png
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from experiments.data_aggregator.tasks import aggregate_tasks_completed
from experiments.data_aggregator.util import collect_results


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

def plot_tasks_completed(data: dict[str, list[int]], scenario: str) -> plt.Figure:
    """Build a bar chart of mean tasks completed per override type.

    Args:
        data: {override_type: [tasks_completed, ...]} from aggregate_tasks_completed
        scenario: used for the chart title
    """
    override_types = sorted(data.keys())
    means = [np.mean(data[ot]) for ot in override_types]
    stds = [np.std(data[ot]) for ot in override_types]
    counts = [len(data[ot]) for ot in override_types]

    fig, ax = plt.subplots(figsize=(7, 5))

    x = np.arange(len(override_types))
    bars = ax.bar(x, means, yerr=stds, capsize=5, width=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels([f"{ot}\n(n={counts[i]})" for i, ot in enumerate(override_types)])
    ax.set_ylabel("Tasks Completed")
    ax.set_title(f"Mean Tasks Completed — {scenario}")
    ax.set_ylim(bottom=0)

    for bar, mean in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            f"{mean:.1f}",
            ha="center", va="bottom", fontsize=10,
        )

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render(fig: plt.Figure, out_path: Path) -> None:
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved to {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.data_visualizer.tasks_completed")
    parser.add_argument("--scenario", required=True, metavar="SCENARIO")
    parser.add_argument("--out", default=None, metavar="FILE")
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else Path(f"{args.scenario}_tasks_completed.png")

    runs = collect_results(args.scenario)
    if not runs:
        raise SystemExit(f"No results with metadata found for {args.scenario}")

    data = aggregate_tasks_completed(runs)
    fig = plot_tasks_completed(data, args.scenario)
    render(fig, out_path)


if __name__ == "__main__":
    main()
