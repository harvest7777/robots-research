"""Unit tests for simulation_view/v2/panels/activity.py."""

from __future__ import annotations

from simulation.domain import TaskId, TaskStatus, Environment, Robot, RobotId, RobotState, WorkTask, SpatialConstraint, TaskState
from simulation.engine_rewrite import Assignment, SimulationState
from simulation.primitives import Position, Time

from simulation_view.terminal.panels.activity import render_activity


def _state(
    robot_pos: Position = Position(1, 2),
    assignments: tuple[Assignment, ...] = (),
    task_done: bool = False,
) -> SimulationState:
    task = WorkTask(
        id=TaskId(1),
        priority=1,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
    )
    ts = TaskState(
        task_id=TaskId(1),
        status=TaskStatus.DONE if task_done else None,
        completed_at=Time(3) if task_done else None,
    )
    return SimulationState(
        environment=Environment(width=10, height=10),
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=robot_pos)},
        tasks={TaskId(1): task},
        task_states={TaskId(1): ts},
        t_now=Time(0),
        assignments=assignments,
    )


def test_shows_activity_header():
    lines = render_activity(_state())
    assert lines[0] == "Activity:"


def test_idle_robot_when_no_assignment():
    lines = render_activity(_state())
    assert any("is idle" in l for l in lines)


def test_working_robot_shows_task():
    a = Assignment(task_id=TaskId(1), robot_id=RobotId(1))
    lines = render_activity(_state(assignments=(a,)))
    assert any("is working on" in l and "Task 1" in l for l in lines)


def test_working_robot_shows_task_name():
    a = Assignment(task_id=TaskId(1), robot_id=RobotId(1))
    lines = render_activity(_state(assignments=(a,)))
    assert any("Work" in l for l in lines)


def test_done_task_assignment_shows_idle():
    a = Assignment(task_id=TaskId(1), robot_id=RobotId(1))
    lines = render_activity(_state(assignments=(a,), task_done=True))
    assert any("is idle" in l for l in lines)
    assert not any("is working on" in l for l in lines)


def test_shows_robot_position():
    # Use coordinates unlikely to collide with battery%, IDs, or other fields.
    lines = render_activity(_state(robot_pos=Position(13, 47)))
    x_shown = any("13.00" in l for l in lines)
    y_shown = any("47.00" in l for l in lines)
    assert x_shown and y_shown
