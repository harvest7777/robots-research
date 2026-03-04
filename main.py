from __future__ import annotations

import argparse
import os
import time

from scenario_loaders import load_simulation
from coordinator_algorithms import simple_assign
from pathfinding_algorithms import astar_pathfind
from services import InMemoryAssignmentService
from simulation_models.assignment import Assignment, RobotId
from simulation_models.task import Task, TaskId, TaskType
from simulation_models.task_state import TaskState
from simulation_models.time import Time
from simulation_view.simulation_view import SimulationView
from simulation_view.terminal_renderer import TerminalRenderer

MAX_DELTA_TIME = 60


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

    sim = load_simulation(args.scenario)

    # Inject a shared IDLE task so any robot can be reassigned to do nothing
    idle_task_id = TaskId(0)
    idle_task = Task(id=idle_task_id, type=TaskType.IDLE, priority=0, required_work_time=Time(0))
    sim.tasks.append(idle_task)
    sim.task_states[idle_task_id] = TaskState(task_id=idle_task_id)
    sim._task_by_id[idle_task_id] = idle_task

    service = InMemoryAssignmentService()
    service.set_assignments(simple_assign(sim.tasks, sim.robots))
    # TEST: at t=5, reassign all robots to idle
    idle_robot_ids = frozenset(RobotId(r.id) for r in sim.robots)
    service.add_assignments([
        Assignment(task_id=idle_task_id, robot_ids=idle_robot_ids, assign_at=Time(5))
    ])
    sim.assignment_service = service
    sim.pathfinding_algorithm = astar_pathfind

    result = sim.run(max_delta_time=MAX_DELTA_TIME)

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
