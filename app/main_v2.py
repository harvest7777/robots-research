import time
from pathlib import Path

from simulation import *
from simulation_view.terminal.terminal_view_service import TerminalViewService

from app.assignment import greedy_assign
from app.starting_objects.environment import build_environment
from app.starting_objects.robots import ROBOTS, ROBOT_STATES
from app.starting_objects.tasks import TASKS, TASK_STATES

_STORAGE = Path(__file__).parent / "storage"
_STORAGE.mkdir(exist_ok=True)

assignments_path = _STORAGE / "sim_assignments_v2.json"
state_path = _STORAGE / "sim_state_v2.json"
registry_path = _STORAGE / "registry_v2.json"

assigner = JsonAssignmentService(assignments_path)
store = JsonSimulationStore(
    registry_path=registry_path,
    state_path=state_path,
    assignment_service=assigner,
)

view = TerminalViewService()
environment = build_environment()

runner = SimulationRunner(
    environment=environment,
    store=store,
    assignment_service=assigner,
    view_service=view
)

for k, v in ROBOT_STATES.items():
    store.add_robot(ROBOTS[k], v)

for k, v in TASK_STATES.items():
    store.add_task(TASKS[k], v)

def _cleanup_storage() -> None:
    for f in _STORAGE.iterdir():
        f.unlink()
    _STORAGE.rmdir()


def _build_state() -> SimulationState:
    robot_states, task_states = store.get_snapshot()
    return SimulationState(
        environment=environment,
        robots={r.id: r for r in store.all_robots()},
        robot_states=robot_states,
        tasks={t.id: t for t in store.all_tasks()},
        task_states=task_states,
        assignments=tuple(assigner.get_current()),
    )


try:
    assigner.update(greedy_assign(_build_state()))

    for _ in range(200):
        state, outcome = runner.step()

        if outcome.tasks_spawned or outcome.tasks_completed:
            assigner.update(greedy_assign(state))

        time.sleep(0.1)
except KeyboardInterrupt:
    pass
    _cleanup_storage()
