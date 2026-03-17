"""
Scenario: multi_robot_parallel

Three robots each assigned to their own task in different corners of the grid.
All three run concurrently and complete independently.

Expected outcome: all three tasks appear in tasks_completed before max_ticks.
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
from simulation.engine_rewrite.step_outcome import StepOutcome


ROBOT_IDS = [RobotId(1), RobotId(2), RobotId(3)]
TASK_IDS  = [TaskId(1),  TaskId(2),  TaskId(3)]

# Each robot starts at a different corner; each task is in the opposite corner.
_ROBOT_STARTS = [Position(0, 0), Position(9, 0), Position(0, 9)]
_TASK_TARGETS = [Position(9, 9), Position(0, 9), Position(9, 0)]


def build() -> SimulationRunner:
    tasks = [
        Task(
            id=TASK_IDS[i],
            type=TaskType.ROUTINE_INSPECTION,
            priority=5,
            required_work_time=Time(5),
            spatial_constraint=SpatialConstraint(target=_TASK_TARGETS[i], max_distance=0),
        )
        for i in range(3)
    ]
    robots = {
        ROBOT_IDS[i]: Robot(id=ROBOT_IDS[i], capabilities=frozenset())
        for i in range(3)
    }
    robot_states = {
        ROBOT_IDS[i]: RobotState(robot_id=ROBOT_IDS[i], position=_ROBOT_STARTS[i])
        for i in range(3)
    }
    state = SimulationState(
        environment=Environment(width=10, height=10),
        robots=robots,
        robot_states=robot_states,
        tasks={t.id: t for t in tasks},
        task_states={},
        t_now=Time(0),
    )
    registry = InMemoryTaskRegistry(tasks=tasks)
    assignment_service = InMemoryAssignmentService(
        assignments=[
            Assignment(task_id=TASK_IDS[i], robot_id=ROBOT_IDS[i])
            for i in range(3)
        ]
    )
    return SimulationRunner(
        state=state,
        registry=registry,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )


def run(max_ticks: int = 200) -> tuple[SimulationState, list[StepOutcome]]:
    runner = build()
    outcomes: list[StepOutcome] = []
    completed: set[TaskId] = set()

    for _ in range(max_ticks):
        state, outcome = runner.step()
        outcomes.append(outcome)
        completed.update(outcome.tasks_completed)
        if completed >= set(TASK_IDS):
            break

    return state, outcomes


if __name__ == "__main__":
    state, outcomes = run()
    completed = {tid for o in outcomes for tid in o.tasks_completed}
    print(f"Finished in {len(outcomes)} ticks — completed tasks: {sorted(completed)}")
