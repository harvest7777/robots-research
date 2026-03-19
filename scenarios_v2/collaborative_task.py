"""
Scenario: collaborative_task

Two robots assigned to the same task, both starting at the task location.
Each robot contributes one work unit per tick, so the task completes in
required_work_time / num_robots ticks when run with full parallel staffing.

Running with num_robots=1 vs num_robots=2 demonstrates that parallel
execution is additive: makespan(2 robots) < makespan(1 robot).

Expected outcome (2 robots): task completes in ~half the ticks of 1 robot.
"""

from __future__ import annotations

from simulation.algorithms import astar_pathfind
from simulation.domain import Environment, Robot, RobotId, RobotState, WorkTask, SpatialConstraint, TaskId
from simulation.primitives import Position, Time
from simulation.engine_rewrite import Assignment, SimulationRunner, SimulationState, StepOutcome
from simulation.engine_rewrite.services import (
    InMemoryAssignmentService, InMemorySimulationRegistry, InMemorySimulationStateService,
)


TASK_ID = TaskId(1)
TASK_WORK_TIME = 10
_TASK_POSITION = Position(5, 5)


def build(num_robots: int = 2) -> SimulationRunner:
    task = WorkTask(
        id=TASK_ID,
        priority=5,
        required_work_time=Time(TASK_WORK_TIME),
        spatial_constraint=SpatialConstraint(target=_TASK_POSITION, max_distance=0),
    )
    robots = [
        Robot(id=RobotId(i), capabilities=frozenset())
        for i in range(1, num_robots + 1)
    ]

    registry = InMemorySimulationRegistry()
    state_service = InMemorySimulationStateService()
    assignment_service = InMemoryAssignmentService(
        assignments=[
            Assignment(task_id=TASK_ID, robot_id=RobotId(i))
            for i in range(1, num_robots + 1)
        ]
    )
    runner = SimulationRunner(
        environment=Environment(width=10, height=10),
        registry=registry,
        state_service=state_service,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )
    # All robots start directly on the task — no travel time, pure work.
    for robot in robots:
        runner.add_robot(robot, RobotState(robot_id=robot.id, position=_TASK_POSITION))
    runner.add_task(task)
    return runner


def run(
    num_robots: int = 2,
    max_ticks: int = 50,
) -> tuple[SimulationState, list[StepOutcome], SimulationRunner]:
    runner = build(num_robots)
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

    from simulation_view.terminal_renderer import TerminalRenderer
    from simulation_view.v2.view import SimulationViewV2

    view = SimulationViewV2()
    renderer = TerminalRenderer()

    def _animate(num_robots: int) -> SimulationRunner:
        runner = build(num_robots)
        try:
            for _ in range(50):
                state, outcome = runner.step()

                terminal = os.get_terminal_size()
                frame = view.render(state, width=terminal.columns, height=terminal.lines)
                renderer.draw(frame)

                if TASK_ID in outcome.tasks_completed:
                    time.sleep(0.5)
                    break

                time.sleep(0.1)
        except Exception:
            renderer.cleanup()
            raise
        return runner

    try:
        solo_runner = _animate(num_robots=1)
        duo_runner  = _animate(num_robots=2)
    finally:
        renderer.cleanup()

    solo = solo_runner.report()
    duo  = duo_runner.report()

    print(f"solo (1 robot):  {solo}")
    print(f"duo  (2 robots): {duo}")
    print(f"speedup: {solo.makespan}t -> {duo.makespan}t")
