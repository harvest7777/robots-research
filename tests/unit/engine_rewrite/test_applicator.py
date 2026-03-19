"""
Unit tests for apply_outcome (Applicator).

Verifies that apply_outcome correctly mutates state from a given StepOutcome
without any business logic — pure mechanical application.
"""

from __future__ import annotations

from simulation.domain import (
    TaskId, TaskStatus, Environment, MoveTask, MoveTaskState, RescuePoint,
    Robot, RobotId, RobotState, SearchTask, SearchTaskState, WorkTask, SpatialConstraint, TaskState,
)
from simulation.primitives import Position, Time
from simulation.engine_rewrite._applicator import apply_outcome
from simulation.engine_rewrite import Assignment, SimulationState, StepOutcome


def _env() -> Environment:
    return Environment(width=20, height=20)


def _base_state() -> SimulationState:
    task = WorkTask(
        id=TaskId(1),
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
    task = WorkTask(
        id=TaskId(1),
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
    task = WorkTask(
        id=TaskId(1),
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
    )
    state = SimulationState(
        environment=_env(),
        robots={
            RobotId(1): Robot(id=RobotId(1), capabilities=frozenset()),
            RobotId(2): Robot(id=RobotId(2), capabilities=frozenset()),
        },
        robot_states={
            RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0)),
            RobotId(2): RobotState(robot_id=RobotId(2), position=Position(0, 0)),
        },
        tasks={TaskId(1): task},
        task_states={TaskId(1): TaskState(task_id=TaskId(1))},
        t_now=Time(0),
    )
    outcome = StepOutcome(worked=[(RobotId(1), TaskId(1)), (RobotId(2), TaskId(1))])
    new_state = apply_outcome(state, outcome)
    assert new_state.task_states[TaskId(1)].work_done == Time(2)


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
    _rp_task = WorkTask(
        id=TaskId(1),
        priority=10,
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
        required_work_time=Time(10),
    )
    rescue_point = RescuePoint(
        id=TaskId(1),
        name="A",
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
        task=_rp_task,
        initial_task_state=TaskState(task_id=TaskId(1)),
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


def test_search_task_marked_done_when_in_tasks_completed():
    search_task = SearchTask(id=TaskId(2), priority=5)
    search_state = SearchTaskState(task_id=TaskId(2), rescue_found=frozenset({TaskId(99)}))
    task = _base_state().tasks[TaskId(1)]
    state = SimulationState(
        environment=_env(),
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={TaskId(1): task, TaskId(2): search_task},
        task_states={TaskId(1): TaskState(task_id=TaskId(1)), TaskId(2): search_state},
        t_now=Time(0),
    )
    outcome = StepOutcome(tasks_completed=[TaskId(2)])
    new_state = apply_outcome(state, outcome)
    updated = new_state.task_states[TaskId(2)]
    assert isinstance(updated, SearchTaskState)
    assert updated.status == TaskStatus.DONE
    assert updated.rescue_found == frozenset({TaskId(99)})  # preserved


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


# ---------------------------------------------------------------------------
# MoveTask position advances
# ---------------------------------------------------------------------------

def _move_task_state(tid: int, cur_x: int, cur_y: int) -> MoveTaskState:
    return MoveTaskState(task_id=TaskId(tid), current_position=Position(cur_x, cur_y))


def _move_task_state_in(tid: int, cur_x: int, cur_y: int, dest_x: int, dest_y: int) -> tuple:
    task = MoveTask(
        id=TaskId(tid),
        priority=5,
        destination=Position(dest_x, dest_y),
        min_robots_required=1,
        min_distance=1,
    )
    ts = MoveTaskState(task_id=TaskId(tid), current_position=Position(cur_x, cur_y))
    return task, ts


def _state_with_move_task(tid: int, cur_x: int, cur_y: int, dest_x: int, dest_y: int) -> SimulationState:
    task, ts = _move_task_state_in(tid, cur_x, cur_y, dest_x, dest_y)
    return SimulationState(
        environment=_env(),
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={TaskId(tid): task},
        task_states={TaskId(tid): ts},
        t_now=Time(0),
    )


def test_tasks_moved_advances_current_position():
    state = _state_with_move_task(1, cur_x=3, cur_y=3, dest_x=8, dest_y=3)
    outcome = StepOutcome(tasks_moved=[(TaskId(1), Position(4, 3))])
    new_state = apply_outcome(state, outcome)
    ts = new_state.task_states[TaskId(1)]
    assert isinstance(ts, MoveTaskState)
    assert ts.current_position == Position(4, 3)


def test_tasks_moved_and_completed_stamps_position_and_done():
    state = _state_with_move_task(1, cur_x=3, cur_y=3, dest_x=4, dest_y=3)
    outcome = StepOutcome(
        tasks_moved=[(TaskId(1), Position(4, 3))],
        tasks_completed=[TaskId(1)],
    )
    new_state = apply_outcome(state, outcome)
    ts = new_state.task_states[TaskId(1)]
    assert isinstance(ts, MoveTaskState)
    assert ts.current_position == Position(4, 3)
    assert ts.status == TaskStatus.DONE
