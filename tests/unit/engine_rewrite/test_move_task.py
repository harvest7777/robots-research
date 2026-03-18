"""
Unit tests for MoveTask business rules.

Covers:
- Robots navigate to the task's current_position
- Task advances one step when >= min_robots_required are present
- Task does NOT advance when < min_robots_required are present
- Task completes when it reaches the destination
- Multiple robots can push a task (min_robots_required > 1)
"""

from __future__ import annotations

import pytest

from simulation.algorithms.astar_pathfinding import astar_pathfind
from simulation.domain.base_task import TaskId, TaskStatus
from simulation.domain.environment import Environment
from simulation.domain.move_task import MoveTask, MoveTaskState
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.primitives.position import Position
from simulation.primitives.time import Time

from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.observer import classify_step
from simulation.engine_rewrite.applicator import apply_outcome
from simulation.engine_rewrite.simulation_state import SimulationState
from simulation.engine_rewrite.step_outcome import IgnoreReason


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(width: int = 10, height: int = 10) -> Environment:
    return Environment(width=width, height=height)


def _robot(rid: int) -> Robot:
    return Robot(id=RobotId(rid), capabilities=frozenset())


def _robot_state(rid: int, x: int, y: int, battery: float = 1.0) -> RobotState:
    return RobotState(robot_id=RobotId(rid), position=Position(x, y), battery_level=battery)


def _move_task(
    tid: int,
    dest_x: int,
    dest_y: int,
    min_robots: int = 1,
) -> MoveTask:
    return MoveTask(
        id=TaskId(tid),
        priority=5,
        destination=Position(dest_x, dest_y),
        min_robots_required=min_robots,
    )


def _move_task_state(tid: int, cur_x: int, cur_y: int) -> MoveTaskState:
    return MoveTaskState(task_id=TaskId(tid), current_position=Position(cur_x, cur_y))


def _state(
    tasks: dict,
    task_states: dict,
    robots: dict,
    robot_states: dict,
    assignments: tuple,
    env: Environment | None = None,
) -> SimulationState:
    return SimulationState(
        environment=env or _env(),
        tasks=tasks,
        task_states=task_states,
        robots=robots,
        robot_states=robot_states,
        assignments=assignments,
    )


# ---------------------------------------------------------------------------
# Navigation: robot moves toward task's current_position
# ---------------------------------------------------------------------------

def test_robot_navigates_to_task_current_position():
    """Robot assigned to a MoveTask moves toward the task's current_position."""
    task = _move_task(1, dest_x=5, dest_y=0)
    ts = _move_task_state(1, cur_x=3, cur_y=0)
    robot = _robot(1)
    rs = _robot_state(1, x=0, y=0)

    state = _state(
        tasks={TaskId(1): task},
        task_states={TaskId(1): ts},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): rs},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)

    # Robot should be moving right toward (3, 0)
    assert len(outcome.moved) == 1
    _, new_pos = outcome.moved[0]
    assert new_pos == Position(1, 0)


# ---------------------------------------------------------------------------
# Task does NOT advance when robot is not yet at current_position
# ---------------------------------------------------------------------------

def test_task_does_not_advance_when_robot_not_at_position():
    """Task stays put if no robot is co-located at current_position."""
    task = _move_task(1, dest_x=5, dest_y=0)
    ts = _move_task_state(1, cur_x=3, cur_y=0)
    robot = _robot(1)
    rs = _robot_state(1, x=0, y=0)  # far away

    state = _state(
        tasks={TaskId(1): task},
        task_states={TaskId(1): ts},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): rs},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)

    assert outcome.tasks_moved == []
    assert outcome.tasks_completed == []


# ---------------------------------------------------------------------------
# Task advances one step when robot arrives
# ---------------------------------------------------------------------------

def test_task_advances_one_step_when_robot_at_position():
    """Task moves one step toward destination when robot is co-located."""
    task = _move_task(1, dest_x=5, dest_y=0)
    ts = _move_task_state(1, cur_x=3, cur_y=0)
    robot = _robot(1)
    rs = _robot_state(1, x=3, y=0)  # already at task position

    state = _state(
        tasks={TaskId(1): task},
        task_states={TaskId(1): ts},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): rs},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)

    assert outcome.tasks_moved == [(TaskId(1), Position(4, 0))]
    assert outcome.tasks_completed == []


# ---------------------------------------------------------------------------
# Applicator applies the new position to MoveTaskState
# ---------------------------------------------------------------------------

def test_applicator_updates_move_task_state_position():
    """apply_outcome advances MoveTaskState.current_position."""
    task = _move_task(1, dest_x=5, dest_y=0)
    ts = _move_task_state(1, cur_x=3, cur_y=0)
    robot = _robot(1)
    rs = _robot_state(1, x=3, y=0)

    state = _state(
        tasks={TaskId(1): task},
        task_states={TaskId(1): ts},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): rs},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)
    new_state = apply_outcome(state, outcome)

    new_ts = new_state.task_states[TaskId(1)]
    assert isinstance(new_ts, MoveTaskState)
    assert new_ts.current_position == Position(4, 0)


# ---------------------------------------------------------------------------
# Task completes when it reaches the destination
# ---------------------------------------------------------------------------

def test_task_completes_on_reaching_destination():
    """MoveTask is marked completed when it reaches destination."""
    task = _move_task(1, dest_x=4, dest_y=0)
    ts = _move_task_state(1, cur_x=3, cur_y=0)  # one step away
    robot = _robot(1)
    rs = _robot_state(1, x=3, y=0)

    state = _state(
        tasks={TaskId(1): task},
        task_states={TaskId(1): ts},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): rs},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)

    assert (TaskId(1), Position(4, 0)) in outcome.tasks_moved
    assert TaskId(1) in outcome.tasks_completed


def test_applicator_marks_completed_task_done():
    task = _move_task(1, dest_x=4, dest_y=0)
    ts = _move_task_state(1, cur_x=3, cur_y=0)
    robot = _robot(1)
    rs = _robot_state(1, x=3, y=0)

    state = _state(
        tasks={TaskId(1): task},
        task_states={TaskId(1): ts},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): rs},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)
    new_state = apply_outcome(state, outcome)

    new_ts = new_state.task_states[TaskId(1)]
    assert isinstance(new_ts, MoveTaskState)
    assert new_ts.current_position == Position(4, 0)
    assert new_ts.status == TaskStatus.DONE


# ---------------------------------------------------------------------------
# min_robots_required > 1: task blocked until enough robots
# ---------------------------------------------------------------------------

def test_task_blocked_when_not_enough_robots():
    """Task does not advance if fewer than min_robots_required are present."""
    task = _move_task(1, dest_x=5, dest_y=0, min_robots=2)
    ts = _move_task_state(1, cur_x=3, cur_y=0)
    robot = _robot(1)
    rs = _robot_state(1, x=3, y=0)  # only 1 robot present

    state = _state(
        tasks={TaskId(1): task},
        task_states={TaskId(1): ts},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): rs},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)

    assert outcome.tasks_moved == []


def test_task_advances_when_enough_robots():
    """Task advances when >= min_robots_required robots are co-located."""
    task = _move_task(1, dest_x=5, dest_y=0, min_robots=2)
    ts = _move_task_state(1, cur_x=3, cur_y=0)
    robot1 = _robot(1)
    robot2 = _robot(2)
    rs1 = _robot_state(1, x=3, y=0)
    rs2 = _robot_state(2, x=3, y=0)

    # Two robots assigned to the same task, both already at current_position.
    # They can't both physically be at the same cell per collision rules, but
    # in this test they start there to verify the counting logic works.
    state = _state(
        tasks={TaskId(1): task},
        task_states={TaskId(1): ts},
        robots={RobotId(1): robot1, RobotId(2): robot2},
        robot_states={RobotId(1): rs1, RobotId(2): rs2},
        assignments=(
            Assignment(task_id=TaskId(1), robot_id=RobotId(1)),
            Assignment(task_id=TaskId(1), robot_id=RobotId(2)),
        ),
    )
    outcome = classify_step(state, astar_pathfind)

    assert outcome.tasks_moved == [(TaskId(1), Position(4, 0))]


# ---------------------------------------------------------------------------
# _next_move_position: step direction logic
# ---------------------------------------------------------------------------

def test_next_move_prefers_x_axis():
    from simulation.engine_rewrite.observer import _next_move_position
    assert _next_move_position(Position(0, 0), Position(3, 3)) == Position(1, 0)


def test_next_move_y_axis_when_x_aligned():
    from simulation.engine_rewrite.observer import _next_move_position
    assert _next_move_position(Position(3, 0), Position(3, 3)) == Position(3, 1)


def test_next_move_stays_at_destination():
    from simulation.engine_rewrite.observer import _next_move_position
    assert _next_move_position(Position(3, 3), Position(3, 3)) == Position(3, 3)


def test_next_move_negative_direction():
    from simulation.engine_rewrite.observer import _next_move_position
    assert _next_move_position(Position(5, 2), Position(2, 2)) == Position(4, 2)
