"""Unit tests for simulation_view/v2/panels/header.py."""

from __future__ import annotations

from simulation.domain.base_task import TaskId
from simulation.domain.environment import Environment
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.task import WorkTask
from simulation.domain.task_state import TaskState
from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.simulation_state import SimulationState
from simulation.primitives.position import Position
from simulation.primitives.time import Time

from simulation_view.v2.panels.header import render_header


def _minimal_state(
    t: int = 0,
    assignments: tuple[Assignment, ...] = (),
) -> SimulationState:
    task = WorkTask(id=TaskId(1), priority=1)
    return SimulationState(
        environment=Environment(width=5, height=5),
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={TaskId(1): task},
        task_states={TaskId(1): TaskState(task_id=TaskId(1))},
        t_now=Time(t),
        assignments=assignments,
    )


def test_shows_current_tick():
    lines = render_header(_minimal_state(t=42))
    assert lines[0] == "t=42"


def test_shows_assignments_label():
    lines = render_header(_minimal_state())
    assert any("Assignments:" in l for l in lines)


def test_no_assignments_shows_none():
    lines = render_header(_minimal_state(assignments=()))
    assert any("(none)" in l for l in lines)


def test_single_assignment():
    a = Assignment(task_id=TaskId(1), robot_id=RobotId(1))
    lines = render_header(_minimal_state(assignments=(a,)))
    assert any("R1" in l and "Task 1" in l for l in lines)


def test_multiple_robots_same_task_grouped():
    task = WorkTask(id=TaskId(1), priority=1)
    state = SimulationState(
        environment=Environment(width=5, height=5),
        robots={
            RobotId(1): Robot(id=RobotId(1), capabilities=frozenset()),
            RobotId(2): Robot(id=RobotId(2), capabilities=frozenset()),
        },
        robot_states={
            RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0)),
            RobotId(2): RobotState(robot_id=RobotId(2), position=Position(1, 0)),
        },
        tasks={TaskId(1): task},
        task_states={TaskId(1): TaskState(task_id=TaskId(1))},
        t_now=Time(0),
        assignments=(
            Assignment(task_id=TaskId(1), robot_id=RobotId(1)),
            Assignment(task_id=TaskId(1), robot_id=RobotId(2)),
        ),
    )
    lines = render_header(state)
    grouped = [l for l in lines if "Task 1" in l]
    assert len(grouped) == 1
    assert "R1" in grouped[0] and "R2" in grouped[0]
