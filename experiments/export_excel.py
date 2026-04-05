"""
experiments/export_excel.py

Exports a single results.json file into an Excel workbook with five sheets:
  - summary          (1 row — simulation + agent flat metrics)
  - robots           (1 row per robot)
  - tasks            (1 row per task)
  - assignment_ignores (1 row per reason)
  - tool_calls       (1 row per tool name)

Usage (from repo root):
    python -m experiments.export_excel --path experiments/scenario_06/baseline/runs/asi1-20260401-211439/results.json
    python -m experiments.export_excel --path path/to/results.json --out my_output.xlsx
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

def _summary_rows(meta: dict, sim: dict, agent: dict) -> list[list]:
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


def _robots_rows(meta: dict, sim: dict, agent: dict, all_robot_ids: list[int]) -> list[list]:
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


def _tasks_rows(meta: dict, sim: dict, agent: dict, all_task_ids: list[int]) -> list[list]:
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


def _assignment_ignores_rows(meta: dict, sim: dict, agent: dict) -> list[list]:
    scenario = meta["scenario"]
    override_type = meta["override_type"]
    llm = meta["llm"]
    run_id = _create_run_id(meta)
    return [
        [scenario, override_type, llm, run_id, reason, count]
        for reason, count in sim.get("assignment_ignores_by_reason", {}).items()
    ]


def _tool_calls_rows(meta: dict, sim: dict, agent: dict) -> list[list]:
    scenario = meta["scenario"]
    override_type = meta["override_type"]
    llm = meta["llm"]
    run_id = _create_run_id(meta)
    return [
        [scenario, override_type, llm, run_id, tool_name, count]
        for tool_name, count in agent.get("total_tool_calls_by_name", {}).items()
    ]


# ---------------------------------------------------------------------------
# Excel writer
# ---------------------------------------------------------------------------

def _write_sheet(ws, headers: list[str], rows: list[list]) -> None:
    ws.append(headers)
    for row in rows:
        ws.append(row)


def export(path: Path, out_path: Path) -> None:
    data = json.loads(path.read_text())
    meta = data["metadata"]
    sim = data["simulation"]
    agent = data["agent"]

    all_robot_ids: list[int] = meta["all_robot_ids"]
    all_task_ids: list[int] = meta["all_task_ids"]

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default empty sheet

    simple_sheets = [
        ("summary", SUMMARY_HEADERS, _summary_rows(meta, sim, agent)),
        ("assignment_ignores", ASSIGNMENT_IGNORES_HEADERS, _assignment_ignores_rows(meta, sim, agent)),
        ("tool_calls", TOOL_CALLS_HEADERS, _tool_calls_rows(meta, sim, agent)),
        ("robots", ROBOTS_HEADERS, _robots_rows(meta, sim, agent, all_robot_ids)),
        ("tasks", TASKS_HEADERS, _tasks_rows(meta, sim, agent, all_task_ids)),
    ]
    for sheet_name, headers, rows in simple_sheets:
        ws = wb.create_sheet(sheet_name)
        _write_sheet(ws, headers, rows)
        print(f"  {sheet_name}: {len(rows)} rows")

    wb.save(out_path)
    print(f"\nSaved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.export_excel")
    parser.add_argument("--path", required=True, metavar="FILE", help="Path to results.json")
    parser.add_argument("--out", default="results.xlsx", metavar="FILE")
    args = parser.parse_args()
    export(Path(args.path), Path(args.out))


if __name__ == "__main__":
    main()
