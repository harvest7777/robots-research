from simulation_view.base_simulation_view import BaseViewService

from simulation_view.terminal.terminal_renderer import TerminalRenderer
from simulation_view.terminal.view import SimulationViewV2

import os
class TerminalViewService(BaseViewService):
    def __init__(self):
        cols, rows = os.get_terminal_size()
        self._cols = cols
        self._rows = rows
        self._view_assembler = SimulationViewV2()
        self._view_renderer = TerminalRenderer()

    def render(self, new_state):
        frame = self._view_assembler.render(new_state, self._cols, self._rows)
        self._view_renderer.draw(frame)

    def handle_event(self):
        self._view_renderer.cleanup()
