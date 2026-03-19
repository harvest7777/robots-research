"""
Robots panel: one line per robot showing id, position, and battery level.
"""

from __future__ import annotations

from simulation.engine_rewrite import SimulationState
from simulation_view.v2.symbols import ROBOT_SYMBOL


def render_robots(state: SimulationState) -> list[str]:
    """Return one line per robot with id, position, and battery percentage."""
    lines: list[str] = ["Robots:"]
    for robot_id in sorted(state.robots):
        rs = state.robot_states[robot_id]
        lines.append(
            f"  {ROBOT_SYMBOL} Robot {robot_id}"
            f"  pos=({rs.position.x:.2f},{rs.position.y:.2f})"
            f"  battery={rs.battery_level:.0%}"
        )
    return lines
