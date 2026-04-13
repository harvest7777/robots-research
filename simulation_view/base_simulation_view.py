"""
BaseSimulationView:

Abstract class for the simulation view. Exposes rendering and shutdown
methods. How the view implements this isn't our concern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from simulation.domain.simulation_state import SimulationState

class BaseViewService(ABC):

    @abstractmethod
    def render(self, simulation_state: SimulationState):
        """Render the current state of the simulation."""

    def handle_exit(self):
        """Gracefully call any cleanup/shutdown behaviors."""

    def is_running(self) -> bool:
        """Return False if the view has been closed and rendering should stop."""
        return True

