"""
experiments/data_aggregator/tasks.py

Aggregation functions for task-level metrics across a set of runs.

All functions take `runs: list[dict]` (loaded results.json dicts) and return
raw grouped values — no summarization. The caller decides how to visualize
(mean bar, box plot, etc.).

Return shape is always `dict[override_type, ...]` so baseline and
structured_override can be compared directly.

None values (e.g. a task that never completed in a run) are excluded from
lists so plot functions never need to handle them.
"""


def aggregate_completion_tick_by_task(
    runs: list[dict],
) -> dict[str, dict[int, list[int]]]:
    """Completion tick for each task, grouped by override type.

    Returns: {override_type: {task_id: [completion_tick, ...]}}
    Only includes ticks for runs where the task actually completed.
    """
    result: dict[str, dict[int, list[int]]] = {}
    for run in runs:
        override_type = run["metadata"]["override_type"]
        completion_ticks = run["simulation"].get("task_completion_tick", {})
        group = result.setdefault(override_type, {})
        for task_id_str, tick in completion_ticks.items():
            group.setdefault(int(task_id_str), []).append(tick)
    return result


def aggregate_ticks_to_complete_by_task(
    runs: list[dict],
) -> dict[str, dict[int, list[int]]]:
    """Ticks from first work applied to completion, grouped by override type.

    Returns: {override_type: {task_id: [ticks_to_complete, ...]}}
    Only includes values for runs where the task completed.
    """
    result: dict[str, dict[int, list[int]]] = {}
    for run in runs:
        override_type = run["metadata"]["override_type"]
        ticks_to_complete = run["simulation"].get("task_ticks_to_complete", {})
        group = result.setdefault(override_type, {})
        for task_id_str, ticks in ticks_to_complete.items():
            group.setdefault(int(task_id_str), []).append(ticks)
    return result


def aggregate_ticks_actively_worked_by_task(
    runs: list[dict],
) -> dict[str, dict[int, list[int]]]:
    """Ticks where at least one robot worked on each task, grouped by override type.

    Returns: {override_type: {task_id: [ticks_actively_worked, ...]}}
    Includes all tasks that received any work, even if not completed.
    """
    result: dict[str, dict[int, list[int]]] = {}
    for run in runs:
        override_type = run["metadata"]["override_type"]
        ticks_worked = run["simulation"].get("task_ticks_actively_worked", {})
        group = result.setdefault(override_type, {})
        for task_id_str, ticks in ticks_worked.items():
            group.setdefault(int(task_id_str), []).append(ticks)
    return result


def aggregate_tasks_completed(runs: list[dict]) -> dict[str, list[int]]:
    """Total tasks completed per run, grouped by override type.

    Returns: {override_type: [tasks_completed, ...]}
    """
    result: dict[str, list[int]] = {}
    for run in runs:
        override_type = run["metadata"]["override_type"]
        result.setdefault(override_type, []).append(
            run["simulation"]["tasks_completed"]
        )
    return result


def aggregate_tasks_failed(runs: list[dict]) -> dict[str, list[int]]:
    """Total tasks failed per run, grouped by override type.

    Returns: {override_type: [tasks_failed, ...]}
    """
    result: dict[str, list[int]] = {}
    for run in runs:
        override_type = run["metadata"]["override_type"]
        result.setdefault(override_type, []).append(
            run["simulation"]["tasks_failed"]
        )
    return result


def aggregate_work_tasks_never_started(runs: list[dict]) -> dict[str, list[int]]:
    """Count of work tasks never started per run, grouped by override type.

    Returns: {override_type: [never_started_count, ...]}
    """
    result: dict[str, list[int]] = {}
    for run in runs:
        override_type = run["metadata"]["override_type"]
        result.setdefault(override_type, []).append(
            run["simulation"]["work_tasks_never_started_count"]
        )
    return result
