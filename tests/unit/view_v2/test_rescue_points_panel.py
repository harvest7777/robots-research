"""Unit tests for simulation_view/v2/panels/rescue_points.py."""

from __future__ import annotations

from simulation.domain import (
    TaskId, Environment, RescuePoint, Robot, RobotId, RobotState,
    SearchTask, SearchTaskState, SpatialConstraint, WorkTask, TaskState,
)
from simulation.engine_rewrite import SimulationState
from simulation.primitives import Position, Time

from simulation_view.v2.panels.rescue_points import render_rescue_points


def _rp(task_id: int = 10, name: str = "Base Camp", x: int = 3, y: int = 4) -> RescuePoint:
    _task = WorkTask(
        id=TaskId(task_id),
        priority=1,
        spatial_constraint=SpatialConstraint(target=Position(x, y), max_distance=0),
    )
    return RescuePoint(
        id=TaskId(task_id),
        name=name,
        spatial_constraint=SpatialConstraint(target=Position(x, y), max_distance=0),
        task=_task,
        initial_task_state=TaskState(task_id=TaskId(task_id)),
    )


def _state(
    rescue_points: list[RescuePoint] | None = None,
    found_ids: frozenset[TaskId] = frozenset(),
) -> SimulationState:
    env = Environment(width=10, height=10)
    search_task = SearchTask(id=TaskId(1), priority=1)
    for rp in (rescue_points or []):
        env.add_rescue_point(rp)
    ts = SearchTaskState(task_id=TaskId(1), rescue_found=found_ids)
    return SimulationState(
        environment=env,
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={TaskId(1): search_task},
        task_states={TaskId(1): ts},
        t_now=Time(0),
    )


def test_empty_when_no_rescue_points():
    lines = render_rescue_points(_state())
    assert lines == []


def test_shows_header_when_rescue_points_exist():
    lines = render_rescue_points(_state(rescue_points=[_rp()]))
    assert lines[0] == "Rescue Points:"


def test_shows_rescue_point_name():
    lines = render_rescue_points(_state(rescue_points=[_rp(name="Alpha")]))
    assert any("Alpha" in l for l in lines)


def test_shows_rescue_point_position():
    lines = render_rescue_points(_state(rescue_points=[_rp(x=5, y=7)]))
    assert any("5" in l and "7" in l for l in lines)


def test_unfound_rescue_point():
    rp = _rp(task_id=10)
    lines = render_rescue_points(_state(rescue_points=[rp], found_ids=frozenset()))
    rp_lines = [l for l in lines if "Base Camp" in l]
    assert len(rp_lines) == 1
    assert "FOUND!" not in rp_lines[0]


def test_found_rescue_point():
    rp = _rp(task_id=10)
    lines = render_rescue_points(
        _state(rescue_points=[rp], found_ids=frozenset([TaskId(10)]))
    )
    assert any("FOUND!" in l for l in lines)


def test_one_line_per_rescue_point():
    rps = [
        _rp(task_id=10, name="Alpha", x=1, y=1),
        _rp(task_id=11, name="Beta", x=2, y=2),
    ]
    lines = render_rescue_points(_state(rescue_points=rps))
    rp_lines = [l for l in lines if l.strip().startswith("^")]
    assert len(rp_lines) == 2
