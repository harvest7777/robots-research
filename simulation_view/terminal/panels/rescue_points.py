"""
Rescue points panel: one line per rescue point showing name, position, and
found/unfound status.

Only rendered when rescue points exist in the environment.
"""

from __future__ import annotations

from simulation.domain import TaskId, SearchTaskState
from simulation.domain import SimulationState

from simulation_view.terminal.symbols import RESCUE_POINT_SYMBOL


def render_rescue_points(state: SimulationState) -> list[str]:
    """Return one line per rescue point with found/unfound status.

    Returns an empty list if the environment has no rescue points.
    """
    if not state.environment.rescue_points:
        return []

    rescue_found: set[TaskId] = set()
    for ts in state.task_states.values():
        if isinstance(ts, SearchTaskState):
            rescue_found.update(ts.rescue_found)

    lines: list[str] = ["Rescue Points:"]
    for rp in sorted(state.environment.rescue_points.values(), key=lambda r: r.id):
        found = rp.id in rescue_found
        status = "FOUND!" if found else "      "
        symbol = " " if found else RESCUE_POINT_SYMBOL
        lines.append(
            f"  {symbol} [{status}] {rp.name}"
            f" at ({rp.position.x},{rp.position.y})"
        )
    return lines
