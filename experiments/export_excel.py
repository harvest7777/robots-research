"""
experiments/export_excel.py

Exports all runs for a scenario into an Excel workbook with five sheets:
  - summary          (1 row per run — simulation + agent flat metrics)
  - robots           (1 row per robot per run)
  - tasks            (1 row per task per run)
  - assignment_ignores (1 row per reason per run)
  - tool_calls       (1 row per tool name per run)

Usage (from repo root):
    python -m experiments.export_excel --scenario scenario_05
    python -m experiments.export_excel --scenario scenario_05 --out my_output.xlsx
"""

import argparse
import json
from pathlib import Path

import openpyxl


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_run_id(meta: dict) -> str:
    return f'{meta["llm"]}-{meta["timestamp"]}'


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------

SUMMARY_HEADERS = [
    "scenario", "override_type", "llm", "run_id",
    "total_ticks", "makespan", "tasks_completed", "tasks_failed",
    "work_tasks_never_started_count",
    "agent_total_calls", "tokens_in", "tokens_out",
    "mean_latency_ms", "min_latency_ms", "max_latency_ms",
    "mean_tool_rounds", "decisions_truncated_by_tool_limit",
]

ROBOTS_HEADERS = [
    "scenario", "override_type", "llm", "run_id", "robot_id",
    "ticks_working", "ticks_moving", "ticks_idle", "ticks_stuck",
    "battery_remaining",
]

TASKS_HEADERS = [
    "scenario", "override_type", "llm", "run_id", "task_id",
    "completion_tick", "ticks_to_complete", "ticks_actively_worked",
]

ASSIGNMENT_IGNORES_HEADERS = [
    "scenario", "override_type", "llm", "run_id", "reason", "count",
]

TOOL_CALLS_HEADERS = [
    "scenario", "override_type", "llm", "run_id", "tool_name", "count",
]


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def _build_summary_rows(meta: dict, sim: dict, agent: dict) -> list[list]:
    scenario = meta["scenario"]
    override_type = meta["override_type"]
    llm = meta["llm"]
    run_id = _create_run_id(meta)
    return [[
        scenario, override_type, llm, run_id,
        sim["total_ticks"], sim["makespan"],
        sim["tasks_completed"], sim["tasks_failed"],
        sim["work_tasks_never_started_count"],
        agent["total_calls"], agent["total_tokens_in"], agent["total_tokens_out"],
        agent["mean_latency_ms"], agent["min_latency_ms"], agent["max_latency_ms"],
        agent["mean_tool_rounds"], agent["decisions_truncated_by_tool_limit"],
    ]]


def _build_robot_rows(meta: dict, sim: dict, all_robot_ids: list[int]) -> list[list]:
    scenario = meta["scenario"]
    override_type = meta["override_type"]
    llm = meta["llm"]
    run_id = _create_run_id(meta)
    rows = []
    for rid in all_robot_ids:
        key = str(rid)
        rows.append([
            scenario, override_type, llm, run_id, rid,
            sim.get("robot_ticks_working", {}).get(key, 0),
            sim.get("robot_ticks_moving", {}).get(key, 0),
            sim.get("robot_ticks_idle", {}).get(key, 0),
            sim.get("robot_ticks_stuck", {}).get(key, 0),
            sim.get("robot_battery_remaining", {}).get(key),
        ])
    return rows


def _build_task_rows(meta: dict, sim: dict, all_task_ids: list[int]) -> list[list]:
    scenario = meta["scenario"]
    override_type = meta["override_type"]
    llm = meta["llm"]
    run_id = _create_run_id(meta)
    rows = []
    for tid in all_task_ids:
        key = str(tid)
        rows.append([
            scenario, override_type, llm, run_id, tid,
            sim.get("task_completion_tick", {}).get(key),
            sim.get("task_ticks_to_complete", {}).get(key),
            sim.get("task_ticks_actively_worked", {}).get(key),
        ])
    return rows


def _build_assignment_ignore_rows(meta: dict, sim: dict) -> list[list]:
    scenario = meta["scenario"]
    override_type = meta["override_type"]
    llm = meta["llm"]
    run_id = _create_run_id(meta)
    return [
        [scenario, override_type, llm, run_id, reason, count]
        for reason, count in sim.get("assignment_ignores_by_reason", {}).items()
    ]


def _build_tool_call_rows(meta: dict, agent: dict) -> list[list]:
    scenario = meta["scenario"]
    override_type = meta["override_type"]
    llm = meta["llm"]
    run_id = _create_run_id(meta)
    return [
        [scenario, override_type, llm, run_id, tool_name, count]
        for tool_name, count in agent.get("total_tool_calls_by_name", {}).items()
    ]


# ---------------------------------------------------------------------------
# Collect
# ---------------------------------------------------------------------------

EXPERIMENTS_DIR = Path(__file__).parent


def _collect_results(scenario: str) -> list[dict]:
    results = []
    for results_path in sorted((EXPERIMENTS_DIR / scenario).glob("*/runs/*/results.json")):
        data = json.loads(results_path.read_text())
        if "metadata" not in data:
            print(f"  skipping {results_path} (no metadata)")
            continue
        results.append(data)
    return results


# ---------------------------------------------------------------------------
# Excel writer
# ---------------------------------------------------------------------------

def _write_sheet(ws, headers: list[str], rows: list[list]) -> None:
    ws.append(headers)
    for row in rows:
        ws.append(row)


def export(scenario: str, out_path: Path) -> None:
    runs = _collect_results(scenario)
    if not runs:
        raise SystemExit(f"No results with metadata found for {scenario}")

    print(f"Found {len(runs)} run(s) for {scenario}")

    summary_rows: list[list] = []
    assignment_ignore_rows: list[list] = []
    tool_call_rows: list[list] = []
    robot_rows: list[list] = []
    task_rows: list[list] = []

    for data in runs:
        meta = data["metadata"]
        sim = data["simulation"]
        agent = data["agent"]
        summary_rows += _build_summary_rows(meta, sim, agent)
        assignment_ignore_rows += _build_assignment_ignore_rows(meta, sim)
        tool_call_rows += _build_tool_call_rows(meta, agent)
        robot_rows += _build_robot_rows(meta, sim, meta["all_robot_ids"])
        task_rows += _build_task_rows(meta, sim, meta["all_task_ids"])

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default empty sheet

    sheets = [
        ("summary", SUMMARY_HEADERS, summary_rows),
        ("assignment_ignores", ASSIGNMENT_IGNORES_HEADERS, assignment_ignore_rows),
        ("tool_calls", TOOL_CALLS_HEADERS, tool_call_rows),
        ("robots", ROBOTS_HEADERS, robot_rows),
        ("tasks", TASKS_HEADERS, task_rows),
    ]
    for sheet_name, headers, rows in sheets:
        ws = wb.create_sheet(sheet_name)
        _write_sheet(ws, headers, rows)
        print(f"  {sheet_name}: {len(rows)} rows")

    wb.save(out_path)
    print(f"\nSaved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.export_excel")
    parser.add_argument("--scenario", required=True, metavar="SCENARIO")
    parser.add_argument("--out", default=None, metavar="FILE")
    args = parser.parse_args()
    out_path = Path(args.out) if args.out else Path(f"{args.scenario}.xlsx")
    export(args.scenario, out_path)


if __name__ == "__main__":
    main()
