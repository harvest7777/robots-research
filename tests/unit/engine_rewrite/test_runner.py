"""
Tests for SimulationRunner — orchestration of registry, assignment service, and engine step.
"""

from __future__ import annotations

from simulation.algorithms import astar_pathfind
from simulation.domain import (
    TaskId, Environment, RescuePoint, Robot, RobotId, RobotState,
    WorkTask, SpatialConstraint, TaskState,
)
from simulation.primitives import Capability, Position, Time
from simulation.engine_rewrite import Assignment, SimulationRunner, SimulationState
from simulation.engine_rewrite.services import InMemoryAssignmentService, InMemoryTaskRegistry


def _base_task() -> WorkTask:
    return WorkTask(
        id=TaskId(1),
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
    )


def _base_state(task: WorkTask | None = None) -> SimulationState:
    t = task or _base_task()
    return SimulationState(
        environment=Environment(width=10, height=10),
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={t.id: t},
        task_states={t.id: TaskState(task_id=t.id)},
        t_now=Time(0),
    )


def test_step_reads_assignments_from_service():
    task = _base_task()
    state = _base_state(task)
    registry = InMemoryTaskRegistry(tasks=[task])
    assignment_service = InMemoryAssignmentService(
        assignments=[Assignment(task_id=TaskId(1), robot_id=RobotId(1))]
    )
    runner = SimulationRunner(
        state=state,
        registry=registry,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )
    _, outcome = runner.step()
    # Robot is assigned but not at the task location — should have moved, not worked
    assert RobotId(1) in [robot_id for robot_id, _ in outcome.moved]


def test_step_syncs_externally_added_tasks_from_registry():
    task = _base_task()
    state = _base_state(task)
    registry = InMemoryTaskRegistry(tasks=[task])
    assignment_service = InMemoryAssignmentService()
    runner = SimulationRunner(
        state=state,
        registry=registry,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )

    new_task = WorkTask(
        id=TaskId(2),
        priority=3,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(9, 9), max_distance=0),
    )
    registry.add(new_task)

    new_state, _ = runner.step()
    assert TaskId(2) in new_state.tasks


def test_step_adds_spawned_tasks_to_registry():
    # When a rescue point is discovered, the runner must surface it to the
    # registry so it becomes available for assignment in subsequent steps.
    from simulation.domain import SearchTask, SearchTaskState

    rescue = RescuePoint(
        id=TaskId(2),
        priority=10,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(0, 0), max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )
    env = Environment(width=10, height=10)
    env.add_rescue_point(rescue)

    search = SearchTask(id=TaskId(1), priority=5)
    robot = Robot(
        id=RobotId(1),
        capabilities=frozenset({Capability.VISION}),
        battery_drain_per_unit_of_movement=0.0,
        battery_drain_per_unit_of_work_execution=0.0,
        battery_drain_per_tick_idle=0.0,
    )
    state = SimulationState(
        environment=env,
        robots={RobotId(1): robot},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={TaskId(1): search},
        task_states={
            TaskId(1): SearchTaskState(
                task_id=TaskId(1),
                rescue_found=frozenset(),
            )
        },
        t_now=Time(0),
    )

    registry = InMemoryTaskRegistry(tasks=[search])
    assignment_service = InMemoryAssignmentService(
        assignments=[Assignment(task_id=TaskId(1), robot_id=RobotId(1))]
    )
    runner = SimulationRunner(
        state=state,
        registry=registry,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )

    runner.step()
    assert registry.get(TaskId(2)) is not None
