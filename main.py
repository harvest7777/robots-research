from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from scenario_loaders import load_simulation
from coordinator_algorithms import simple_assign
from pathfinding_algorithms import astar_pathfind
from services import (
    JsonAssignmentService,
    JsonSimulationStateService,
    RobotStateSnapshot,
    SimulationState,
    TaskStateSnapshot,
)
from simulation_models.assignment import Assignment, RobotId
from simulation_models.snapshot import SimulationSnapshot
from simulation_models.task import Task, TaskId, TaskType
from simulation_models.task_state import TaskState
from simulation_models.time import Time
from simulation_view.simulation_view import SimulationView
from simulation_view.terminal_renderer import TerminalRenderer

MAX_DELTA_TIME = 60

_STATE_PATH = Path(__file__).parent / "sim_state.json"
_ASSIGNMENTS_PATH = Path(__file__).parent / "sim_assignments.json"


def _snapshot_to_simulation_state(
    scenario_id: str, snapshot: SimulationSnapshot
) -> SimulationState:
    robots = [
        RobotStateSnapshot(
            robot_id=robot_id,
            x=state.position.x,
            y=state.position.y,
            battery_level=state.battery_level,
        )
        for robot_id, state in snapshot.robot_states.items()
    ]
    tasks = [
        TaskStateSnapshot(
            task_id=task_id,
            status=state.status,
            work_done_ticks=state.work_done.tick,
            assigned_robot_ids=list(state.assigned_robot_ids),
        )
        for task_id, state in snapshot.task_states.items()
    ]
    return SimulationState(
        scenario_id=scenario_id,
        tick=snapshot.t_now.tick if snapshot.t_now else 0,
        robots=robots,
        tasks=tasks,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load and run a simulation scenario")
    parser.add_argument("scenario", help="Path to the scenario JSON file")
    parser.add_argument(
        "--renderer",
        choices=["terminal", "mujoco"],
        default="terminal",
        help="Renderer to use (default: terminal)",
    )
    args = parser.parse_args()

    scenario_id = str(Path(args.scenario).stem)

    sim = load_simulation(args.scenario)

    # Inject a shared IDLE task so any robot can be reassigned to do nothing
    idle_task_id = TaskId(0)
    idle_task = Task(id=idle_task_id, type=TaskType.IDLE, priority=0, required_work_time=Time(0))
    sim.tasks.append(idle_task)
    sim.task_states[idle_task_id] = TaskState(task_id=idle_task_id)
    sim._task_by_id[idle_task_id] = idle_task

    # --- Fresh run: seed both JSON files ---
    assignment_service = JsonAssignmentService(_ASSIGNMENTS_PATH)
    assignment_service.set_assignments(simple_assign(sim.tasks, sim.robots))

    state_service = JsonSimulationStateService(_STATE_PATH)
    initial_state = _snapshot_to_simulation_state(scenario_id, sim.snapshot())
    state_service.write(initial_state)

    sim.assignment_service = assignment_service
    sim.pathfinding_algorithm = astar_pathfind

    def on_tick(snapshot: SimulationSnapshot) -> None:
        state_service.write(_snapshot_to_simulation_state(scenario_id, snapshot))

    result = sim.run(max_delta_time=MAX_DELTA_TIME, on_tick=on_tick)

    if args.renderer == "mujoco":
        from simulation_view.mujoco_renderer import MuJoCoRenderer

        renderer = MuJoCoRenderer()
        try:
            for snapshot in result.snapshots:
                renderer.update(snapshot)
                time.sleep(0.5)
            renderer.wait_for_close()
        finally:
            renderer.cleanup()
    else:
        renderer = TerminalRenderer()
        try:
            for snapshot in result.snapshots:
                cols, rows = os.get_terminal_size()
                frame = SimulationView(snapshot).render(cols, rows)
                renderer.draw(frame)
                time.sleep(1)
        finally:
            renderer.cleanup()


if __name__ == "__main__":
    main()
