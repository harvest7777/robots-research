from simulation import *
from simulation_view.terminal_renderer import TerminalRenderer
from pathlib import Path
from shutil import get_terminal_size

from simulation_view.v2.view import SimulationViewV2

assignments_path = Path("sim_assignments_v2.json")
state_path = Path("sim_state_v2.json")
registry_path = Path("registry_v2.json")

assigner = JsonAssignmentService(assignments_path)
registry = JsonSimulationRegistry(registry_path)
state_service = JsonSimulationStateService(state_path, registry=registry, assignment_service=assigner)
environment = Environment(10,10)

runner = SimulationRunner(
    environment=environment,
    registry=registry,
    state_service=state_service,
    assignment_service=assigner,
)

renderer = TerminalRenderer()
view = SimulationViewV2()

state, _outcome = runner.step()
term = get_terminal_size(fallback=(120, 40))
frame = view.render(state, width=term.columns, height=term.lines)
renderer.draw(frame)
renderer.cleanup()
