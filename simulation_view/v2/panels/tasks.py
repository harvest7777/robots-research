"""
Tasks panel: one line per task showing status, label, priority, and progress.
"""

from __future__ import annotations

from simulation.domain import (
    TaskId, MoveTask, MoveTaskState, RescuePoint, SearchTask, SearchTaskState, WorkTask, TaskState,
)
from simulation.domain import SimulationState
from simulation.primitives import Position

from simulation_view.v2.symbols import task_label, task_status_symbol


def render_tasks(state: SimulationState) -> list[str]:
    """Return one line per task with status symbol, label, priority, and progress."""
    lines: list[str] = ["Tasks:"]
    for task_id in sorted(state.tasks):
        task = state.tasks[task_id]
        ts = state.task_states.get(task_id)
        if ts is None:
            continue

        status = task_status_symbol(ts)
        label = task_label(task)

        if isinstance(task, SearchTask):
            assert isinstance(ts, SearchTaskState)
            total = len(state.environment.rescue_points)
            found = len(ts.rescue_found)
            progress = f"  found={found}/{total}"
            spatial = ""
        elif isinstance(task, MoveTask):
            assert isinstance(ts, MoveTaskState)
            progress = f"  pos=({ts.current_position.x},{ts.current_position.y}) dest=({task.destination.x},{task.destination.y})"
            spatial = ""
        else:
            assert isinstance(task, WorkTask) and isinstance(ts, TaskState)
            progress = f"  progress={ts.work_done.tick}/{task.required_work_time.tick}"
            spatial = _spatial_info(task)

        lines.append(
            f"  {status} [{label}] Task {task_id}"
            f"  priority={task.priority}"
            f"{progress}"
            f"{spatial}"
        )
    return lines


def _spatial_info(task: WorkTask) -> str:
    sc = task.spatial_constraint
    if sc is None:
        return ""
    if isinstance(sc.target, Position):
        s = f"  at ({sc.target.x},{sc.target.y})"
        if sc.max_distance > 0:
            s += f" r={sc.max_distance}"
        return s
    return f"  zone={int(sc.target)}"
