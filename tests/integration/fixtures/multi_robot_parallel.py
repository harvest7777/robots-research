"""
Scenario: multi_robot_parallel

Three robots each assigned to their own task in different corners of the grid.
All three run concurrently and complete independently.

Expected outcome: all three tasks appear in tasks_completed before max_ticks.
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


ROBOT_IDS = [RobotId(1), RobotId(2), RobotId(3)]
TASK_IDS  = [TaskId(1),  TaskId(2),  TaskId(3)]

# Each robot starts at a different corner; each task is in the opposite corner.
_ROBOT_STARTS = [Position(0, 0), Position(9, 0), Position(0, 9)]
_TASK_TARGETS = [Position(9, 9), Position(0, 9), Position(9, 0)]


def build() -> SimulationRunner:
    tasks = [
        WorkTask(
            id=TASK_IDS[i],
            priority=5,
            required_work_time=Time(5),
            spatial_constraint=SpatialConstraint(target=_TASK_TARGETS[i], max_distance=0),
        )
        for i in range(3)
    ]
    robots = [Robot(id=ROBOT_IDS[i], capabilities=frozenset()) for i in range(3)]

    store = InMemorySimulationStore()
    assignment_service = InMemoryAssignmentService(
        assignments=[
            Assignment(task_id=TASK_IDS[i], robot_id=ROBOT_IDS[i])
            for i in range(3)
        ]
    )
    runner = SimulationRunner(
        environment=Environment(width=10, height=10),
        store=store,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )
    for i in range(3):
        store.add_robot(robots[i], RobotState(robot_id=ROBOT_IDS[i], position=_ROBOT_STARTS[i]))
        store.add_task(tasks[i], TaskState(task_id=TASK_IDS[i]))
    return runner


def run(max_ticks: int = 200) -> tuple[SimulationState, list[StepOutcome], SimulationRunner]:
    runner = build()
    outcomes: list[StepOutcome] = []
    completed: set[TaskId] = set()

    for _ in range(max_ticks):
        state, outcome = runner.step()
        outcomes.append(outcome)
        completed.update(outcome.tasks_completed)
        if completed >= set(TASK_IDS):
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
    completed: set[TaskId] = set()

    try:
        for _ in range(200):
            state, outcome = runner.step()
            outcomes.append(outcome)
            completed.update(outcome.tasks_completed)

            terminal = os.get_terminal_size()
            frame = view.render(state, width=terminal.columns, height=terminal.lines)
            renderer.draw(frame)

            if completed >= set(TASK_IDS):
                time.sleep(0.5)
                break

            time.sleep(0.1)
    finally:
        renderer.cleanup()

    print(runner.stop())
