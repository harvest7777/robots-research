from simulation import *
from simulation_view.terminal_renderer import TerminalRenderer
from pathlib import Path
from .environment import build_environment
from .robots import ROBOTS, ROBOT_STATES
from .tasks import TASKS, TASK_STATES

from simulation_view.v2.view import SimulationViewV2

assignments_path = Path("sim_assignments_v2.json")
state_path = Path("sim_state_v2.json")
registry_path = Path("registry_v2.json")

assigner = JsonAssignmentService(assignments_path)
store = JsonSimulationStore(
    registry_path=registry_path,
    state_path=state_path,
    assignment_service=assigner,
)
environment = build_environment()

runner = SimulationRunner(
    environment=environment,
    store=store,
    assignment_service=assigner,
    view=True
)

renderer = TerminalRenderer()
view = SimulationViewV2()
for k, v in ROBOT_STATES.items():
    store.add_robot(ROBOTS[k], v)

for k, v in TASK_STATES.items():
    store.add_task(TASKS[k], v)

state, _outcome = runner.step()
