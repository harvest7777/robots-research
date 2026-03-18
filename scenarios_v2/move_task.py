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

from simulation.algorithms.astar_pathfinding import astar_pathfind
from simulation.domain.environment import Environment
from simulation.domain.move_task import MoveTask, MoveTaskState
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.base_task import TaskId
from simulation.primitives.position import Position
from simulation.primitives.time import Time

from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.runner import SimulationRunner
from simulation.engine_rewrite.simulation_state import SimulationState
from simulation.engine_rewrite.services.in_memory_assignment_service import InMemoryAssignmentService
from simulation.engine_rewrite.services.in_memory_task_registry import InMemoryTaskRegistry
from simulation.engine_rewrite.step_outcome import StepOutcome


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
    task_state = MoveTaskState(task_id=MOVE_TASK_ID, current_position=_START)

    robots = {rid: Robot(id=rid, capabilities=frozenset()) for rid in ROBOT_IDS}
    robot_states = {
        RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0)),
        RobotId(2): RobotState(robot_id=RobotId(2), position=Position(_WIDTH - 1, _HEIGHT - 1)),
    }

    state = SimulationState(
        environment=Environment(width=_WIDTH, height=_HEIGHT),
        robots=robots,
        robot_states=robot_states,
        tasks={MOVE_TASK_ID: task},
        task_states={MOVE_TASK_ID: task_state},
        t_now=Time(0),
    )
    registry = InMemoryTaskRegistry(tasks=[task])
    assignment_service = InMemoryAssignmentService(
        assignments=[
            Assignment(task_id=MOVE_TASK_ID, robot_id=rid)
            for rid in ROBOT_IDS
        ]
    )
    return SimulationRunner(
        state=state,
        registry=registry,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )


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

    from simulation_view.terminal_renderer import TerminalRenderer
    from simulation_view.v2.view import SimulationViewV2

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

    print(runner.report())
