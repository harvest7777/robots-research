"""
SimulationViewV2: assembler that stamps panel lines into a Frame.

No rendering logic lives here — each section is delegated to a panel
function that returns list[str]. The assembler owns layout: it decides
the section order and handles row overflow (terminal too small).
"""

from __future__ import annotations

from simulation.engine_rewrite.simulation_state import SimulationState

from simulation_view.frame import Frame, make_frame, stamp
from simulation_view.v2.panels.activity import render_activity
from simulation_view.v2.panels.environment import render_environment
from simulation_view.v2.panels.header import render_header
from simulation_view.v2.panels.rescue_points import render_rescue_points
from simulation_view.v2.panels.robots import render_robots
from simulation_view.v2.panels.tasks import render_tasks


class SimulationViewV2:
    """Assembler: calls panels, stamps lines into a Frame, handles overflow."""

    def render(self, state: SimulationState, width: int, height: int) -> Frame:
        """Build a fully populated Frame from the state."""
        frame = make_frame(width, height)

        sections: list[list[str]] = [
            render_header(state),
            [""],
            render_environment(state),
            [""],
            render_robots(state),
            [""],
            render_tasks(state),
            [""],
        ]

        rescue_lines = render_rescue_points(state)
        if rescue_lines:
            sections.append(rescue_lines)
            sections.append([""])

        sections.append(render_activity(state))

        row = 0
        for section in sections:
            for line in section:
                if row >= len(frame):
                    return frame
                stamp(frame, row, 0, line)
                row += 1

        return frame
