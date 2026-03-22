"""
Scenario: move_task

Two robots carry a heavy object from the left side of the map to the right.
The object starts at (1, 10) and must reach (18, 10). Both robots are required
to be adjacent to the object before it can move — one robot alone cannot shift it.

The robots begin on opposite sides of the object (above and below), then push
it east across the full width of the 20x20 grid.

Expected outcome: MOVE_TASK_ID appears in tasks_completed before max_ticks.
"""

from __future__ import annotations

from simulation.algorithms import astar_pathfind
from simulation.domain import Environment, MoveTask, MoveTaskState, Robot, RobotId, RobotState, TaskId
from simulation.primitives import Position
from simulation.engine_rewrite import Assignment, SimulationRunner, SimulationState, StepOutcome
from simulation.engine_rewrite.services import (
    InMemoryAssignmentService, InMemorySimulationStore,
)


MOVE_TASK_ID = TaskId(1)
ROBOT_IDS = [RobotId(1), RobotId(2)]

_START   = Position(1, 10)
_DEST    = Position(18, 10)
_WIDTH   = 20
_HEIGHT  = 20


def build() -> SimulationRunner:
    task = MoveTask(
        id=MOVE_TASK_ID,
        priority=5,
        destination=_DEST,
        min_robots_required=2,
        min_distance=1,
    )
    robots = [Robot(id=rid, capabilities=frozenset()) for rid in ROBOT_IDS]

    store = InMemorySimulationStore()
    assignment_service = InMemoryAssignmentService(
        assignments=[
            Assignment(task_id=MOVE_TASK_ID, robot_id=rid)
            for rid in ROBOT_IDS
        ]
    )
    runner = SimulationRunner(
        environment=Environment(width=_WIDTH, height=_HEIGHT),
        store=store,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )
    store.add_robot(robots[0], RobotState(robot_id=RobotId(1), position=Position(0, 0)))
    store.add_robot(robots[1], RobotState(robot_id=RobotId(2), position=Position(_WIDTH - 1, _HEIGHT - 1)))
    store.add_task(task, MoveTaskState(task_id=MOVE_TASK_ID, current_position=_START))
    return runner


def run(max_ticks: int = 200) -> tuple[SimulationState, list[StepOutcome], SimulationRunner]:
    runner = build()
    outcomes: list[StepOutcome] = []

    for _ in range(max_ticks):
        state, outcome = runner.step()
        outcomes.append(outcome)
        if MOVE_TASK_ID in outcome.tasks_completed:
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

    try:
        for _ in range(200):
            state, outcome = runner.step()

            terminal = os.get_terminal_size()
            frame = view.render(state, width=terminal.columns, height=terminal.lines)
            renderer.draw(frame)

            if MOVE_TASK_ID in outcome.tasks_completed:
                time.sleep(1.0)
                break

            time.sleep(0.1)
    finally:
        renderer.cleanup()

    print(runner.stop())
