"""
Unit tests for apply_outcome (Applicator).

Verifies that apply_outcome correctly mutates state from a given StepOutcome
without any business logic — pure mechanical application.
"""

from __future__ import annotations

from simulation.domain.base_task import TaskId, TaskStatus
from simulation.domain.environment import Environment
from simulation.domain.rescue_point import RescuePoint
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.search_task import SearchTask, SearchTaskState
from simulation.domain.task import Task, TaskType, SpatialConstraint
from simulation.domain.task_state import TaskState
from simulation.primitives.position import Position
from simulation.primitives.time import Time

from simulation.engine_rewrite.applicator import apply_outcome
from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.simulation_state import SimulationState
from simulation.engine_rewrite.step_outcome import StepOutcome


def _env() -> Environment:
    return Environment(width=20, height=20)


def _base_state() -> SimulationState:
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
    )
    return SimulationState(
        environment=_env(),
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={TaskId(1): task},
        task_states={TaskId(1): TaskState(task_id=TaskId(1))},
        t_now=Time(0),
    )


# ---------------------------------------------------------------------------
# Robot position and battery
# ---------------------------------------------------------------------------

def test_moved_robot_updates_position():
    state = _base_state()
    outcome = StepOutcome(moved=[(RobotId(1), Position(1, 0))])
    new_state = apply_outcome(state, outcome)
    assert new_state.robot_states[RobotId(1)].position == Position(1, 0)


def test_moved_robot_drains_move_battery():
    state = _base_state()
    robot = state.robots[RobotId(1)]
    outcome = StepOutcome(moved=[(RobotId(1), Position(1, 0))])
    new_state = apply_outcome(state, outcome)
    assert new_state.robot_states[RobotId(1)].battery_level == pytest.approx(
        1.0 - robot.battery_drain_per_unit_of_movement
    )


def test_worked_robot_drains_work_battery():
    state = _base_state()
    robot = state.robots[RobotId(1)]
    outcome = StepOutcome(worked=[(RobotId(1), TaskId(1))])
    new_state = apply_outcome(state, outcome)
    assert new_state.robot_states[RobotId(1)].battery_level == pytest.approx(
        1.0 - robot.battery_drain_per_unit_of_work_execution
    )


def test_idle_robot_drains_idle_battery():
    state = _base_state()
    robot = state.robots[RobotId(1)]
    outcome = StepOutcome()  # robot not in moved or worked
    new_state = apply_outcome(state, outcome)
    assert new_state.robot_states[RobotId(1)].battery_level == pytest.approx(
        1.0 - robot.battery_drain_per_tick_idle
    )


def test_battery_does_not_go_below_zero():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
    )
    state = SimulationState(
        environment=_env(),
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0), battery_level=0.0)},
        tasks={TaskId(1): task},
        task_states={TaskId(1): TaskState(task_id=TaskId(1))},
        t_now=Time(0),
    )
    outcome = StepOutcome(moved=[(RobotId(1), Position(1, 0))])
    new_state = apply_outcome(state, outcome)
    assert new_state.robot_states[RobotId(1)].battery_level == 0.0


# ---------------------------------------------------------------------------
# Work progress
# ---------------------------------------------------------------------------

def test_work_accumulates_on_worked_task():
    state = _base_state()
    outcome = StepOutcome(worked=[(RobotId(1), TaskId(1))])
    new_state = apply_outcome(state, outcome)
    task_state = new_state.task_states[TaskId(1)]
    assert isinstance(task_state, TaskState)
    assert task_state.work_done == Time(1)


def test_two_robots_contribute_two_ticks():
    state = _base_state()
    state.robots[RobotId(2)] = Robot(id=RobotId(2), capabilities=frozenset())
    state.robot_states[RobotId(2)] = RobotState(robot_id=RobotId(2), position=Position(0, 0))
    outcome = StepOutcome(worked=[(RobotId(1), TaskId(1)), (RobotId(2), TaskId(1))])
    new_state = apply_outcome(state, outcome)
    task_state = new_state.task_states[TaskId(1)]
    assert isinstance(task_state, TaskState)
    assert task_state.work_done == Time(2)


def test_started_at_set_on_first_work():
    state = _base_state()
    outcome = StepOutcome(worked=[(RobotId(1), TaskId(1))])
    new_state = apply_outcome(state, outcome)
    task_state = new_state.task_states[TaskId(1)]
    assert isinstance(task_state, TaskState)
    assert task_state.started_at == Time(0)  # state.t_now before advancing


# ---------------------------------------------------------------------------
# Task completion
# ---------------------------------------------------------------------------

def test_completed_task_is_marked_done():
    state = _base_state()
    outcome = StepOutcome(tasks_completed=[TaskId(1)])
    new_state = apply_outcome(state, outcome)
    assert new_state.task_states[TaskId(1)].status == TaskStatus.DONE


def test_completed_task_has_completed_at_set():
    state = _base_state()
    outcome = StepOutcome(tasks_completed=[TaskId(1)])
    new_state = apply_outcome(state, outcome)
    assert new_state.task_states[TaskId(1)].completed_at == Time(1)  # t_now + 1


# ---------------------------------------------------------------------------
# Spawned tasks
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Search task state
# ---------------------------------------------------------------------------

def test_rescue_point_marked_found_in_search_state():
    env = _env()
    rescue_point = RescuePoint(
        id=TaskId(1),
        priority=10,
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
        required_work_time=Time(10),
        name="A",
    )
    env.add_rescue_point(rescue_point)

    search_task = SearchTask(id=TaskId(1), priority=5)
    search_state = SearchTaskState(task_id=TaskId(1), rescue_found=frozenset())
    state = SimulationState(
        environment=env,
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={TaskId(1): search_task},
        task_states={TaskId(1): search_state},
        t_now=Time(0),
    )
    outcome = StepOutcome(rescue_points_found=[TaskId(1)])
    new_state = apply_outcome(state, outcome)
    updated_task_state = new_state.task_states[TaskId(1)]
    assert isinstance(updated_task_state, SearchTaskState)
    assert TaskId(1) in updated_task_state.rescue_found


# ---------------------------------------------------------------------------
# Time and immutability
# ---------------------------------------------------------------------------

def test_t_now_advances_by_one():
    state = _base_state()
    outcome = StepOutcome()
    new_state = apply_outcome(state, outcome)
    assert new_state.t_now == Time(1)


def test_apply_outcome_does_not_mutate_input_state():
    state = _base_state()
    original_pos = state.robot_states[RobotId(1)].position
    outcome = StepOutcome(moved=[(RobotId(1), Position(3, 3))])
    apply_outcome(state, outcome)
    assert state.robot_states[RobotId(1)].position == original_pos


import pytest
