"""Unit tests for simulation_view/v2/panels/robots.py."""

from __future__ import annotations

from simulation.domain import Environment, Robot, RobotId, RobotState
from simulation.engine_rewrite import SimulationState
from simulation.primitives import Position, Time

from simulation_view.terminal.panels.robots import render_robots


def _state_with_robot(
    robot_id: int = 1,
    position: Position = Position(0, 0),
    battery: float = 1.0,
) -> SimulationState:
    rid = RobotId(robot_id)
    return SimulationState(
        environment=Environment(width=5, height=5),
        robots={rid: Robot(id=rid, capabilities=frozenset())},
        robot_states={rid: RobotState(robot_id=rid, position=position, battery_level=battery)},
        tasks={},
        task_states={},
        t_now=Time(0),
    )


def test_shows_robots_header():
    lines = render_robots(_state_with_robot())
    assert lines[0] == "Robots:"


def test_shows_robot_id():
    lines = render_robots(_state_with_robot(robot_id=2))
    assert any("Robot 2" in l for l in lines)


def test_shows_battery_as_percentage():
    lines = render_robots(_state_with_robot(battery=0.5))
    assert any("50%" in l for l in lines)


def test_shows_full_battery():
    lines = render_robots(_state_with_robot(battery=1.0))
    assert any("100%" in l for l in lines)


def test_shows_robot_position():
    # Use coordinates unlikely to appear in battery%, IDs, or other fields.
    lines = render_robots(_state_with_robot(position=Position(13, 47)))
    assert any("13" in l and "47" in l for l in lines)


def test_one_line_per_robot():
    rid1 = RobotId(1)
    rid2 = RobotId(2)
    state = SimulationState(
        environment=Environment(width=5, height=5),
        robots={
            rid1: Robot(id=rid1, capabilities=frozenset()),
            rid2: Robot(id=rid2, capabilities=frozenset()),
        },
        robot_states={
            rid1: RobotState(robot_id=rid1, position=Position(0, 0)),
            rid2: RobotState(robot_id=rid2, position=Position(1, 1)),
        },
        tasks={},
        task_states={},
        t_now=Time(0),
    )
    lines = render_robots(state)
    robot_lines = [l for l in lines if l.strip().startswith("R Robot")]
    assert len(robot_lines) == 2
