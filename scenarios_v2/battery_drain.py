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

from simulation.algorithms.astar_pathfinding import astar_pathfind
from simulation.domain.environment import Environment
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.task import Task, TaskType, SpatialConstraint
from simulation.domain.base_task import TaskId
from simulation.primitives.position import Position
from simulation.primitives.time import Time

from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.runner import SimulationRunner
from simulation.engine_rewrite.simulation_state import SimulationState
from simulation.engine_rewrite.services.in_memory_assignment_service import InMemoryAssignmentService
from simulation.engine_rewrite.services.in_memory_task_registry import InMemoryTaskRegistry
from simulation.engine_rewrite.step_outcome import IgnoreReason, StepOutcome


ROBOT_ID = RobotId(1)
TASK_ID  = TaskId(1)

# 0.002 drain per work tick × 2 ticks = 0.004 total; battery runs out on tick 3.
_STARTING_BATTERY = 0.004


def build() -> SimulationRunner:
    task = Task(
        id=TASK_ID,
        type=TaskType.ROUTINE_INSPECTION,
        priority=5,
        required_work_time=Time(20),
        spatial_constraint=SpatialConstraint(target=Position(3, 3), max_distance=0),
    )
    # Robot starts on the task cell — no movement needed, pure work drain.
    robot = Robot(id=ROBOT_ID, capabilities=frozenset())
    state = SimulationState(
        environment=Environment(width=10, height=10),
        robots={ROBOT_ID: robot},
        robot_states={
            ROBOT_ID: RobotState(
                robot_id=ROBOT_ID,
                position=Position(3, 3),
                battery_level=_STARTING_BATTERY,
            )
        },
        tasks={TASK_ID: task},
        task_states={},
        t_now=Time(0),
    )
    registry = InMemoryTaskRegistry(tasks=[task])
    assignment_service = InMemoryAssignmentService(
        assignments=[Assignment(task_id=TASK_ID, robot_id=ROBOT_ID)]
    )
    return SimulationRunner(
        state=state,
        registry=registry,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )


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

    print(runner.report())
