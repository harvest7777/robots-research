import asyncio
import time
from pathlib import Path

from simulation import *
from simulation_view.mujoco.mujoco_view_service import MujocoViewService

from app.starting_objects.environment import build_environment
from app.starting_objects.robots import ROBOTS, ROBOT_STATES
from app.starting_objects.tasks import TASKS, TASK_STATES
from llm.agent import AssignmentAgent
from llm.providers.openai import OpenAIProvider
from simulation_view.terminal.terminal_view_service import TerminalViewService

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

view = MujocoViewService()
# view = TerminalViewService()
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


_SYSTEM = (
    "You are a robot task assignment system. "
    "Call get_state to inspect the current simulation state, "
    "then call write_assignments to assign each robot to the highest-priority "
    "task it is capable of performing. Prioritise tasks by their priority field."
)

agent = AssignmentAgent(
    provider=OpenAIProvider(),
    store=store,
    assignment_service=assigner,
    system=_SYSTEM,
)

def _agent_assign(prompt: str) -> None:
    print("[agent] assigning...")
    _, tokens = asyncio.run(agent.invoke(prompt, max_tool_calls=3))
    print(f"[agent] done — tokens used: {tokens}")


try:
    _agent_assign("Simulation started. Assign all robots to tasks.")

    for _ in range(50):
        state, outcome = runner.step()

        if outcome.tasks_spawned or outcome.tasks_completed:
            _agent_assign("Tasks changed. Reassign robots as needed.")

        time.sleep(0.5)
    print(runner.stop())
except KeyboardInterrupt:
    pass
    # _cleanup_storage()
