"""
Activity panel: per-robot description of current assignment or idle status.
"""

from __future__ import annotations

from simulation.domain import TaskId, TaskStatus, RobotId
from simulation.engine_rewrite import SimulationState

from simulation_view.v2.symbols import task_full_name


def render_activity(state: SimulationState) -> list[str]:
    """Return one line per robot describing its current assignment or idle status."""
    # Build robot → task map from active (non-terminal) assignments
    robot_task: dict[RobotId, TaskId] = {}
    for a in state.assignments:
        ts = state.task_states.get(a.task_id)
        if ts is not None and ts.status in (TaskStatus.DONE, TaskStatus.FAILED):
            continue
        robot_task[a.robot_id] = a.task_id

    lines: list[str] = ["Activity:"]
    for robot_id in sorted(state.robots):
        rs = state.robot_states[robot_id]
        task_id = robot_task.get(robot_id)
        if task_id is not None:
            task = state.tasks.get(task_id)
            name = task_full_name(task) if task is not None else f"Task {task_id}"
            lines.append(
                f"  Robot {robot_id} ({rs.position.x:.2f},{rs.position.y:.2f})"
                f" is working on {name} (Task {task_id})"
            )
        else:
            lines.append(
                f"  Robot {robot_id} ({rs.position.x:.2f},{rs.position.y:.2f})"
                f" is idle"
            )
    return lines
