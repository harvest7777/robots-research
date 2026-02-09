# SimulationView: stateless renderer for a single SimulationSnapshot.
#
# Receives an immutable SimulationSnapshot and produces a visual
# representation of that moment in time. Owns no simulation state —
# all data comes from the snapshot. This keeps rendering fully
# decoupled from the live Simulation and makes any snapshot in the
# history dict renderable with no extra setup.

from simulation_models.snapshot import SimulationSnapshot


class SimulationView:
    def __init__(self, snapshot: SimulationSnapshot) -> None:
        self.snapshot = snapshot

    def render(self) -> None:
        pass
