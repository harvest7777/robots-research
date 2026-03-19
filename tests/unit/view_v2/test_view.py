"""Unit tests for SimulationViewV2 assembler."""

from __future__ import annotations

from simulation.domain import (
    TaskId, Environment, RescuePoint, Robot, RobotId, RobotState,
    SearchTask, SearchTaskState, WorkTask, SpatialConstraint, TaskState,
)
from simulation.engine_rewrite import Assignment, SimulationState
from simulation.primitives import Position, Time

from simulation_view.frame import frame_to_string
from simulation_view.v2.view import SimulationViewV2


def _base_state(
    assignments: tuple[Assignment, ...] = (),
    rescue_points: list[RescuePoint] | None = None,
) -> SimulationState:
    env = Environment(width=5, height=5)
    task = WorkTask(
        id=TaskId(1),
        priority=3,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(3, 3), max_distance=0),
    )
    for rp in (rescue_points or []):
        env.add_rescue_point(rp)
    return SimulationState(
        environment=env,
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={TaskId(1): task},
        task_states={TaskId(1): TaskState(task_id=TaskId(1))},
        t_now=Time(7),
        assignments=assignments,
    )


def test_render_returns_frame_of_correct_size():
    view = SimulationViewV2()
    frame = view.render(_base_state(), width=80, height=40)
    assert len(frame) == 40
    assert all(len(row) == 80 for row in frame)


def test_render_contains_tick():
    view = SimulationViewV2()
    frame = view.render(_base_state(), width=80, height=40)
    content = frame_to_string(frame)
    assert "t=7" in content


def test_render_contains_robots_section():
    view = SimulationViewV2()
    frame = view.render(_base_state(), width=80, height=40)
    content = frame_to_string(frame)
    assert "Robots:" in content
    assert "Robot 1" in content


def test_render_contains_tasks_section():
    view = SimulationViewV2()
    frame = view.render(_base_state(), width=80, height=40)
    content = frame_to_string(frame)
    assert "Tasks:" in content


def test_render_contains_activity_section():
    view = SimulationViewV2()
    frame = view.render(_base_state(), width=80, height=40)
    content = frame_to_string(frame)
    assert "Activity:" in content


def test_render_contains_environment_grid():
    from simulation_view.v2.symbols import ROBOT_SYMBOL
    view = SimulationViewV2()
    frame = view.render(_base_state(), width=80, height=40)
    lines = frame_to_string(frame)
    # Robot is at (0,0) — confirm its symbol appears in the first grid row.
    assert ROBOT_SYMBOL in lines


def test_rescue_points_section_absent_when_no_rescue_points():
    view = SimulationViewV2()
    frame = view.render(_base_state(), width=80, height=40)
    content = frame_to_string(frame)
    assert "Rescue Points:" not in content


def test_rescue_points_section_present_when_rescue_points_exist():
    _rp_task = WorkTask(
        id=TaskId(10),
        priority=1,
        spatial_constraint=SpatialConstraint(target=Position(2, 2), max_distance=0),
    )
    rp = RescuePoint(
        id=TaskId(10),
        name="Camp",
        spatial_constraint=SpatialConstraint(target=Position(2, 2), max_distance=0),
        task=_rp_task,
        initial_task_state=TaskState(task_id=TaskId(10)),
    )
    view = SimulationViewV2()
    frame = view.render(_base_state(rescue_points=[rp]), width=80, height=50)
    content = frame_to_string(frame)
    assert "Rescue Points:" in content
    assert "Camp" in content


def test_render_graceful_overflow_small_terminal():
    """A very small terminal should not raise; frame is just truncated."""
    view = SimulationViewV2()
    frame = view.render(_base_state(), width=20, height=3)
    assert len(frame) == 3
    # at minimum: tick line should appear
    content = frame_to_string(frame)
    assert "t=7" in content
