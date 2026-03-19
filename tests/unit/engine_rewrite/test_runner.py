"""
Tests for SimulationRunner — orchestration of registry, assignment service, and engine step.
"""

from __future__ import annotations

from simulation.algorithms import astar_pathfind
from simulation.domain import (
    TaskId, Environment, RescuePoint, Robot, RobotId, RobotState,
    WorkTask, SpatialConstraint,
)
from simulation.primitives import Capability, Position, Time
from simulation.engine_rewrite import Assignment, SimulationRunner
from simulation.engine_rewrite.services import (
    InMemoryAssignmentService,
    InMemorySimulationRegistry,
    InMemorySimulationStateService,
)


def _make_runner(
    task: WorkTask | None = None,
    assignments: list[Assignment] | None = None,
) -> tuple[SimulationRunner, InMemorySimulationRegistry]:
    t = task or WorkTask(
        id=TaskId(1),
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
    )
    registry = InMemorySimulationRegistry()
    state_service = InMemorySimulationStateService()
    assignment_service = InMemoryAssignmentService(assignments=assignments or [])
    runner = SimulationRunner(
        environment=Environment(width=10, height=10),
        registry=registry,
        state_service=state_service,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )
    runner.add_robot(
        Robot(id=RobotId(1), capabilities=frozenset()),
        RobotState(robot_id=RobotId(1), position=Position(0, 0)),
    )
    runner.add_task(t)
    return runner, registry


def test_step_reads_assignments_from_service():
    runner, _ = _make_runner(
        assignments=[Assignment(task_id=TaskId(1), robot_id=RobotId(1))]
    )
    _, outcome = runner.step()
    # Robot is assigned but not at the task location — should have moved, not worked
    assert RobotId(1) in [robot_id for robot_id, _ in outcome.moved]


def test_step_syncs_externally_added_tasks_from_registry():
    runner, registry = _make_runner()

    new_task = WorkTask(
        id=TaskId(2),
        priority=3,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(9, 9), max_distance=0),
    )
    runner.add_task(new_task)

    new_state, _ = runner.step()
    assert TaskId(2) in new_state.tasks


def test_step_adds_spawned_tasks_to_registry():
    # When a rescue point is discovered, the runner must surface it to the
    # registry so it becomes available for assignment in subsequent steps.
    from simulation.domain import SearchTask

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

    registry = InMemorySimulationRegistry()
    state_service = InMemorySimulationStateService()
    assignment_service = InMemoryAssignmentService(
        assignments=[Assignment(task_id=TaskId(1), robot_id=RobotId(1))]
    )
    runner = SimulationRunner(
        environment=env,
        registry=registry,
        state_service=state_service,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )
    runner.add_robot(robot, RobotState(robot_id=RobotId(1), position=Position(0, 0)))
    runner.add_task(search)

    runner.step()
    assert registry.get_task(TaskId(2)) is not None
