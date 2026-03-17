"""
Scenario: simple_task_completion

One robot, one task. The robot starts at (0, 0) and the task is at (5, 5).
The robot walks to the task location and works until completion.

Expected outcome: task 1 appears in tasks_completed before max_ticks.
"""

from __future__ import annotations

from simulation.algorithms.astar_pathfinding import astar_pathfind
from simulation.domain.environment import Environment
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.task import Task, TaskType, SpatialConstraint
from simulation.domain.base_task import TaskId
from simulation.primitives.capability import Capability
from simulation.primitives.position import Position
from simulation.primitives.time import Time

from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.runner import SimulationRunner
from simulation.engine_rewrite.simulation_state import SimulationState
from simulation.engine_rewrite.services.in_memory_assignment_service import InMemoryAssignmentService
from simulation.engine_rewrite.services.in_memory_task_registry import InMemoryTaskRegistry
from simulation.engine_rewrite.step_outcome import StepOutcome


ROBOT_ID = RobotId(1)
TASK_ID = TaskId(1)


def build() -> SimulationRunner:
    task = Task(
        id=TASK_ID,
        type=TaskType.ROUTINE_INSPECTION,
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
    )
    robot = Robot(id=ROBOT_ID, capabilities=frozenset())
    state = SimulationState(
        environment=Environment(width=10, height=10),
        robots={ROBOT_ID: robot},
        robot_states={ROBOT_ID: RobotState(robot_id=ROBOT_ID, position=Position(0, 0))},
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


def run(max_ticks: int = 100) -> tuple[SimulationState, list[StepOutcome]]:
    runner = build()
    outcomes: list[StepOutcome] = []

    for _ in range(max_ticks):
        state, outcome = runner.step()
        outcomes.append(outcome)
        if TASK_ID in outcome.tasks_completed:
            break

    return state, outcomes


if __name__ == "__main__":
    state, outcomes = run()
    completed = any(TASK_ID in o.tasks_completed for o in outcomes)
    print(f"Completed in {len(outcomes)} ticks — task done: {completed}")
