"""
Scenario: battery_drain

A robot starts with barely enough battery to do 2 ticks of work (0.004 battery,
0.002 drain per work tick). The task requires 20 ticks of work, so the robot
runs out of battery and the task is never completed.

The robot is placed directly on the task location so no movement drain is
involved — the depletion is purely from work execution.

Expected outcome:
- NO_BATTERY ignore reason appears within the first few ticks.
- Task 1 is never in tasks_completed after max_ticks.
"""

from __future__ import annotations

from simulation.algorithms import astar_pathfind
from simulation.domain import Environment, Robot, RobotId, RobotState, WorkTask, SpatialConstraint, TaskId
from simulation.domain.task_state import TaskState
from simulation.primitives import Position, Time
from simulation.engine_rewrite import Assignment, SimulationRunner, SimulationState, IgnoreReason, StepOutcome
from simulation.engine_rewrite.services import (
    InMemoryAssignmentService, InMemorySimulationRegistry, InMemorySimulationStateService,
)


ROBOT_ID = RobotId(1)
TASK_ID  = TaskId(1)

# 0.002 drain per work tick × 2 ticks = 0.004 total; battery runs out on tick 3.
_STARTING_BATTERY = 0.004
_TASK_POSITION = Position(3, 3)


def build() -> SimulationRunner:
    task = WorkTask(
        id=TASK_ID,
        priority=5,
        required_work_time=Time(20),
        spatial_constraint=SpatialConstraint(target=_TASK_POSITION, max_distance=0),
    )
    # Robot starts on the task cell — no movement needed, pure work drain.
    robot = Robot(id=ROBOT_ID, capabilities=frozenset())

    registry = InMemorySimulationRegistry()
    state_service = InMemorySimulationStateService()
    assignment_service = InMemoryAssignmentService(
        assignments=[Assignment(task_id=TASK_ID, robot_id=ROBOT_ID)]
    )
    runner = SimulationRunner(
        environment=Environment(width=10, height=10),
        registry=registry,
        state_service=state_service,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )
    runner.add_robot(
        robot,
        RobotState(robot_id=ROBOT_ID, position=_TASK_POSITION, battery_level=_STARTING_BATTERY),
    )
    runner.add_task(task, TaskState(task_id=TASK_ID))
    return runner


def run(max_ticks: int = 30) -> tuple[SimulationState, list[StepOutcome], SimulationRunner]:
    runner = build()
    outcomes: list[StepOutcome] = []

    for _ in range(max_ticks):
        state, outcome = runner.step()
        outcomes.append(outcome)

    return state, outcomes, runner


if __name__ == "__main__":
    import os
    import time

    from simulation_view.terminal_renderer import TerminalRenderer
    from simulation_view.v2.view import SimulationViewV2

    runner = build()
    view = SimulationViewV2()
    renderer = TerminalRenderer()
    outcomes: list[StepOutcome] = []

    try:
        for _ in range(30):
            state, outcome = runner.step()
            outcomes.append(outcome)

            terminal = os.get_terminal_size()
            frame = view.render(state, width=terminal.columns, height=terminal.lines)
            renderer.draw(frame)

            time.sleep(0.2)

        time.sleep(0.5)
    finally:
        renderer.cleanup()

    print(runner.stop())
