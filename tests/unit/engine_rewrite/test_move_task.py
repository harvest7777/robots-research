"""
Unit tests for MoveTask business rules in the Observer and Applicator.
"""

from __future__ import annotations

from simulation.algorithms.astar_pathfinding import astar_pathfind
from simulation.domain.base_task import TaskId, TaskStatus
from simulation.domain.environment import Environment
from simulation.domain.move_task import MoveTask, MoveTaskState
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.primitives.position import Position
from simulation.primitives.time import Time

from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite._applicator import apply_outcome
from simulation.engine_rewrite._observer import classify_step
from simulation.engine_rewrite.simulation_state import SimulationState


def _env(width: int = 10, height: int = 10) -> Environment:
    return Environment(width=width, height=height)


def _robot(rid: int) -> Robot:
    return Robot(id=RobotId(rid), capabilities=frozenset())


def _rs(rid: int, x: int, y: int) -> RobotState:
    return RobotState(robot_id=RobotId(rid), position=Position(x, y))


def _task(tid: int, dest_x: int, dest_y: int, min_robots: int = 1, min_distance: int = 1) -> MoveTask:
    return MoveTask(
        id=TaskId(tid),
        priority=5,
        destination=Position(dest_x, dest_y),
        min_robots_required=min_robots,
        min_distance=min_distance,
    )


def _ts(tid: int, cur_x: int, cur_y: int) -> MoveTaskState:
    return MoveTaskState(task_id=TaskId(tid), current_position=Position(cur_x, cur_y))


def _state(
    task: MoveTask,
    task_state: MoveTaskState,
    robots: dict,
    robot_states: dict,
    assignments: tuple,
    env: Environment | None = None,
) -> SimulationState:
    return SimulationState(
        environment=env or _env(),
        tasks={task.id: task},
        task_states={task.id: task_state},
        robots=robots,
        robot_states=robot_states,
        assignments=assignments,
    )


# ---------------------------------------------------------------------------
# Navigation: robot moves toward current_position when far away
# ---------------------------------------------------------------------------

def test_robot_navigates_toward_task_position():
    task = _task(1, dest_x=8, dest_y=0)
    ts = _ts(1, cur_x=4, cur_y=0)
    state = _state(
        task, ts,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _rs(1, x=0, y=0)},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)

    assert len(outcome.moved) == 1
    _, new_pos = outcome.moved[0]
    assert new_pos == Position(1, 0)
    assert outcome.tasks_moved == []


# ---------------------------------------------------------------------------
# Eligibility: min_distance gate
# ---------------------------------------------------------------------------

def test_robot_outside_min_distance_not_eligible():
    task = _task(1, dest_x=8, dest_y=0, min_distance=1)
    ts = _ts(1, cur_x=4, cur_y=0)
    # robot is 3 steps away — not eligible
    state = _state(
        task, ts,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _rs(1, x=1, y=0)},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.tasks_moved == []


def test_robot_within_min_distance_triggers_formation_move():
    task = _task(1, dest_x=8, dest_y=0, min_distance=1)
    ts = _ts(1, cur_x=4, cur_y=0)
    # robot is adjacent (distance 1) — eligible
    state = _state(
        task, ts,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _rs(1, x=3, y=0)},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.tasks_moved == [(TaskId(1), Position(5, 0))]


# ---------------------------------------------------------------------------
# min_robots_required gate
# ---------------------------------------------------------------------------

def test_formation_does_not_move_below_min_robots():
    task = _task(1, dest_x=8, dest_y=0, min_robots=2, min_distance=1)
    ts = _ts(1, cur_x=4, cur_y=0)
    state = _state(
        task, ts,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _rs(1, x=4, y=0)},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.tasks_moved == []


def test_formation_moves_when_min_robots_met():
    task = _task(1, dest_x=8, dest_y=0, min_robots=2, min_distance=1)
    ts = _ts(1, cur_x=4, cur_y=0)
    state = _state(
        task, ts,
        robots={RobotId(1): _robot(1), RobotId(2): _robot(2)},
        robot_states={
            RobotId(1): _rs(1, x=4, y=0),
            RobotId(2): _rs(2, x=3, y=0),
        },
        assignments=(
            Assignment(task_id=TaskId(1), robot_id=RobotId(1)),
            Assignment(task_id=TaskId(1), robot_id=RobotId(2)),
        ),
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.tasks_moved == [(TaskId(1), Position(5, 0))]


# ---------------------------------------------------------------------------
# Rigid body: all formation members shift by the same (dx, dy)
# ---------------------------------------------------------------------------

def test_formation_robots_all_shift_together():
    task = _task(1, dest_x=8, dest_y=0, min_robots=2, min_distance=1)
    ts = _ts(1, cur_x=4, cur_y=0)
    state = _state(
        task, ts,
        robots={RobotId(1): _robot(1), RobotId(2): _robot(2)},
        robot_states={
            RobotId(1): _rs(1, x=4, y=0),
            RobotId(2): _rs(2, x=3, y=0),
        },
        assignments=(
            Assignment(task_id=TaskId(1), robot_id=RobotId(1)),
            Assignment(task_id=TaskId(1), robot_id=RobotId(2)),
        ),
    )
    outcome = classify_step(state, astar_pathfind)

    moved = dict(outcome.moved)
    assert moved[RobotId(1)] == Position(5, 0)
    assert moved[RobotId(2)] == Position(4, 0)
    assert outcome.tasks_moved == [(TaskId(1), Position(5, 0))]


# ---------------------------------------------------------------------------
# Obstacle and robot blocking
# ---------------------------------------------------------------------------

def test_formation_stays_put_when_blocked_by_obstacle():
    env = _env()
    env.add_obstacle(Position(5, 0))
    task = _task(1, dest_x=8, dest_y=0, min_distance=1)
    ts = _ts(1, cur_x=4, cur_y=0)
    state = _state(
        task, ts,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _rs(1, x=4, y=0)},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
        env=env,
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.tasks_moved == []


def test_formation_stays_put_when_blocked_by_other_robot():
    task = _task(1, dest_x=8, dest_y=0, min_distance=1)
    ts = _ts(1, cur_x=4, cur_y=0)
    # Robot 2 is not assigned to the task but occupies the formation's next cell
    state = SimulationState(
        environment=_env(),
        tasks={TaskId(1): task},
        task_states={TaskId(1): ts},
        robots={RobotId(1): _robot(1), RobotId(2): _robot(2)},
        robot_states={
            RobotId(1): _rs(1, x=4, y=0),
            RobotId(2): _rs(2, x=5, y=0),  # blocking
        },
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.tasks_moved == []


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------

def test_task_completes_when_reaching_destination():
    task = _task(1, dest_x=5, dest_y=0, min_distance=1)
    ts = _ts(1, cur_x=4, cur_y=0)
    state = _state(
        task, ts,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _rs(1, x=4, y=0)},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)

    assert outcome.tasks_moved == [(TaskId(1), Position(5, 0))]
    assert TaskId(1) in outcome.tasks_completed


# ---------------------------------------------------------------------------
# Full round-trip: classify_step + apply_outcome
# ---------------------------------------------------------------------------

def test_round_trip_updates_all_positions_and_stamps_completion():
    task = _task(1, dest_x=5, dest_y=0, min_distance=1)
    ts = _ts(1, cur_x=4, cur_y=0)
    state = _state(
        task, ts,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _rs(1, x=4, y=0)},
        assignments=(Assignment(task_id=TaskId(1), robot_id=RobotId(1)),),
    )
    outcome = classify_step(state, astar_pathfind)
    new_state = apply_outcome(state, outcome)

    new_ts = new_state.task_states[TaskId(1)]
    assert isinstance(new_ts, MoveTaskState)
    assert new_ts.current_position == Position(5, 0)
    assert new_ts.status == TaskStatus.DONE
    assert new_state.robot_states[RobotId(1)].position == Position(5, 0)
