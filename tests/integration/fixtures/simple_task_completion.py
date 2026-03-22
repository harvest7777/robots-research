"""
Scenario: simple_task_completion

One robot, one task. The robot starts at (0, 0) and the task is at (5, 5).
The robot walks to the task location and works until completion.

Expected outcome: task 1 appears in tasks_completed before max_ticks.
"""

from __future__ import annotations

from simulation.algorithms import astar_pathfind
from simulation.domain import Environment, Robot, RobotId, RobotState, WorkTask, SpatialConstraint, TaskId
from simulation.domain.task_state import TaskState
from simulation.primitives import Position, Time
from simulation.engine_rewrite import Assignment, SimulationRunner, SimulationState, StepOutcome
from simulation.engine_rewrite.services import (
    InMemoryAssignmentService, InMemorySimulationStore,
)


ROBOT_ID = RobotId(1)
TASK_ID = TaskId(1)


def build() -> SimulationRunner:
    task = WorkTask(
        id=TASK_ID,
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
    )
    robot = Robot(id=ROBOT_ID, capabilities=frozenset())

    store = InMemorySimulationStore()
    assignment_service = InMemoryAssignmentService(
        assignments=[Assignment(task_id=TASK_ID, robot_id=ROBOT_ID)]
    )
    runner = SimulationRunner(
        environment=Environment(width=10, height=10),
        store=store,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )
    store.add_robot(robot, RobotState(robot_id=ROBOT_ID, position=Position(0, 0)))
    store.add_task(task, TaskState(task_id=TASK_ID))
    return runner


def run(max_ticks: int = 100) -> tuple[SimulationState, list[StepOutcome], SimulationRunner]:
    runner = build()
    outcomes: list[StepOutcome] = []

    for _ in range(max_ticks):
        state, outcome = runner.step()
        outcomes.append(outcome)
        if TASK_ID in outcome.tasks_completed:
            break

    return state, outcomes, runner


if __name__ == "__main__":
    import os
    import time

    from simulation_view.terminal.terminal_renderer import TerminalRenderer
    from simulation_view.terminal.view import SimulationViewV2

    runner = build()
    view = SimulationViewV2()
    renderer = TerminalRenderer()
    outcomes: list[StepOutcome] = []

    try:
        for _ in range(100):
            state, outcome = runner.step()
            outcomes.append(outcome)

            terminal = os.get_terminal_size()
            frame = view.render(state, width=terminal.columns, height=terminal.lines)
            renderer.draw(frame)

            if TASK_ID in outcome.tasks_completed:
                time.sleep(0.5)
                break

            time.sleep(0.1)
    finally:
        renderer.cleanup()

    print(runner.stop())
