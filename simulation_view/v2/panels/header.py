"""
Header panel: tick counter and current assignment summary.

Returns one line for the tick, one "Assignments:" label, then one line
per task showing which robots are assigned to it.
"""

from __future__ import annotations

from simulation.domain import TaskId, RobotId
from simulation.engine_rewrite import SimulationState


def render_header(state: SimulationState) -> list[str]:
    """Return lines showing current tick and one line per assignment."""
    lines: list[str] = [f"t={state.t_now.tick}"]

    lines.append("Assignments:")
    task_robots: dict[TaskId, list[RobotId]] = {}
    for a in state.assignments:
        task_robots.setdefault(a.task_id, []).append(a.robot_id)

    if not task_robots:
        lines.append("  (none)")
    else:
        for task_id, robot_ids in sorted(task_robots.items()):
            robots_str = ", ".join(f"R{rid}" for rid in sorted(robot_ids))
            lines.append(f"  {robots_str} \u2192 Task {task_id}")

    return lines
