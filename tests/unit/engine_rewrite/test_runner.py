"""
Tests for SimulationRunner — orchestration of registry, assignment service, and engine step.

Confirms that step() wires services correctly, surfaces spawned tasks to the
registry, and returns (SimulationState, StepOutcome).
"""

from __future__ import annotations

from simulation.algorithms.astar_pathfinding import astar_pathfind
from simulation.domain.base_task import TaskId
from simulation.domain.environment import Environment
from simulation.domain.rescue_point import RescuePoint
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.task import Task, TaskType, SpatialConstraint
from simulation.domain.task_state import TaskState
from simulation.primitives.capability import Capability
from simulation.primitives.position import Position
from simulation.primitives.time import Time

from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.runner import SimulationRunner
from simulation.engine_rewrite.simulation_state import SimulationState
from simulation.engine_rewrite.services.in_memory_assignment_service import InMemoryAssignmentService
from simulation.engine_rewrite.services.in_memory_task_registry import InMemoryTaskRegistry


def _base_task() -> Task:
    return Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
    )


def _base_state(task: Task | None = None) -> SimulationState:
    t = task or _base_task()
    return SimulationState(
        environment=Environment(width=10, height=10),
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={t.id: t},
        task_states={t.id: TaskState(task_id=t.id)},
        t_now=Time(0),
    )


def _runner(state: SimulationState | None = None, task: Task | None = None) -> SimulationRunner:
    t = task or _base_task()
    s = state or _base_state(t)
    registry = InMemoryTaskRegistry(tasks=[t])
    assignment_service = InMemoryAssignmentService()
    return SimulationRunner(
        state=s,
        registry=registry,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
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

    new_task = Task(
        id=TaskId(2),
        type=TaskType.ROUTINE_INSPECTION,
        priority=3,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(9, 9), max_distance=0),
    )
    registry.add(new_task)

    new_state, _ = runner.step()
    assert TaskId(2) in new_state.tasks


def test_unassigned_task_has_no_task_state():
    # A task in the registry that is never assigned should produce no
    # task_states entry — there is nothing to track until work begins.
    task = _base_task()
    unassigned_task = Task(
        id=TaskId(2),
        type=TaskType.ROUTINE_INSPECTION,
        priority=3,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(9, 9), max_distance=0),
    )
    state = SimulationState(
        environment=Environment(width=10, height=10),
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={task.id: task},
        task_states={task.id: TaskState(task_id=task.id)},
        t_now=Time(0),
    )
    registry = InMemoryTaskRegistry(tasks=[task, unassigned_task])
    assignment_service = InMemoryAssignmentService()
    runner = SimulationRunner(
        state=state,
        registry=registry,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )

    new_state, _ = runner.step()
    assert TaskId(2) not in new_state.task_states


def test_step_adds_spawned_tasks_to_registry():
    # Build a search task scenario where a rescue point gets discovered,
    # producing a tasks_spawned entry that should land in the registry.
    from simulation.domain.search_task import SearchTask, SearchTaskState

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

    _, outcome = runner.step()
    assert TaskId(2) in outcome.rescue_points_found
    assert registry.get(TaskId(2)) is not None
