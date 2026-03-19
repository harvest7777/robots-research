"""Unit tests for simulation_view/v2/panels/environment.py."""

from __future__ import annotations

from simulation.domain import (
    TaskId, TaskStatus, Environment, RescuePoint, Robot, RobotId, RobotState,
    SearchTask, SearchTaskState, WorkTask, SpatialConstraint, TaskState,
)
from simulation.engine_rewrite import SimulationState
from simulation.primitives import Position, Time, Zone, ZoneId, ZoneType

from simulation_view.v2.panels.environment import render_environment
from simulation_view.v2.symbols import (
    ROBOT_SYMBOL,
    OBSTACLE_SYMBOL,
    TASK_AREA_SYMBOL,
    RESCUE_POINT_SYMBOL,
    EMPTY_SYMBOL,
)


def _state(
    width: int = 5,
    height: int = 5,
    robot_pos: Position | None = None,
    tasks: dict | None = None,
    task_states: dict | None = None,
    env_extra=None,
) -> SimulationState:
    env = Environment(width=width, height=height)
    if env_extra:
        env_extra(env)
    if robot_pos is not None:
        robots = {RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())}
        robot_states = {RobotId(1): RobotState(robot_id=RobotId(1), position=robot_pos)}
    else:
        robots = {}
        robot_states = {}
    return SimulationState(
        environment=env,
        robots=robots,
        robot_states=robot_states,
        tasks=tasks or {},
        task_states=task_states or {},
        t_now=Time(0),
    )


def _cell(lines: list[str], x: int, y: int) -> str:
    """Extract the symbol at grid position (x, y) from rendered lines."""
    return lines[y].split()[x]


def test_empty_grid_fills_with_empty_symbol():
    lines = render_environment(_state(width=3, height=3))
    assert all(s == EMPTY_SYMBOL for row in lines for s in row.split())


def test_row_count_matches_height():
    lines = render_environment(_state(width=4, height=6))
    assert len(lines) == 6


def test_robot_symbol_at_position():
    lines = render_environment(_state(robot_pos=Position(2, 1), width=5, height=5))
    assert _cell(lines, 2, 1) == ROBOT_SYMBOL


def test_obstacle_symbol():
    def add_obstacle(env):
        env.add_obstacle(Position(1, 0))

    lines = render_environment(_state(env_extra=add_obstacle))
    assert _cell(lines, 1, 0) == OBSTACLE_SYMBOL


def test_task_target_shows_task_id():
    task = WorkTask(
        id=TaskId(3),
        priority=1,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(2, 2), max_distance=0),
    )
    lines = render_environment(
        _state(
            tasks={TaskId(3): task},
            task_states={TaskId(3): TaskState(task_id=TaskId(3))},
        )
    )
    assert _cell(lines, 2, 2) == "3"


def test_task_area_symbol_within_radius():
    task = WorkTask(
        id=TaskId(1),
        priority=1,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(2, 2), max_distance=1),
    )
    lines = render_environment(
        _state(
            tasks={TaskId(1): task},
            task_states={TaskId(1): TaskState(task_id=TaskId(1))},
        )
    )
    # target cell shows task id, adjacent cells show area symbol
    assert _cell(lines, 2, 2) == "1"
    assert _cell(lines, 2, 1) == TASK_AREA_SYMBOL


def test_done_task_not_rendered():
    task = WorkTask(
        id=TaskId(1),
        priority=1,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(2, 2), max_distance=0),
    )
    ts = TaskState(task_id=TaskId(1), status=TaskStatus.DONE, completed_at=Time(1))
    lines = render_environment(
        _state(tasks={TaskId(1): task}, task_states={TaskId(1): ts})
    )
    assert _cell(lines, 2, 2) == EMPTY_SYMBOL


def test_rescue_point_symbol():
    rp = RescuePoint(
        id=TaskId(1),
        priority=1,
        name="RP1",
        spatial_constraint=SpatialConstraint(target=Position(3, 3), max_distance=0),
    )

    def setup(env: Environment):
        env.add_rescue_point(rp)

    lines = render_environment(_state(env_extra=setup))
    assert _cell(lines, 3, 3) == RESCUE_POINT_SYMBOL


def test_robot_takes_priority_over_obstacle():
    """Robot rendered at obstacle position overrides obstacle symbol.

    robot_states are separate from the grid — the render checks
    robot_positions first, so a robot at an obstacle cell shows ROBOT_SYMBOL.
    """
    # Obstacle at (1,0); robot also placed at (1,0) via robot_states only
    # (not through env.place, so no conflict in the grid data structure).
    def add_obstacle(env):
        env.add_obstacle(Position(1, 0))

    env = Environment(width=5, height=5)
    add_obstacle(env)
    state = SimulationState(
        environment=env,
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(1, 0))},
        tasks={},
        task_states={},
        t_now=Time(0),
    )
    lines = render_environment(state)
    assert _cell(lines, 1, 0) == ROBOT_SYMBOL


def test_search_task_not_rendered_on_grid():
    """SearchTask has no fixed target — grid should remain empty."""
    task = SearchTask(id=TaskId(1), priority=1)
    lines = render_environment(
        _state(
            tasks={TaskId(1): task},
            task_states={TaskId(1): SearchTaskState(task_id=TaskId(1))},
        )
    )
    assert all(s == EMPTY_SYMBOL for row in lines for s in row.split())
