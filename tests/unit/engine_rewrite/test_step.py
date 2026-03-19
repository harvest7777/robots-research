"""
Tests for step() — the thin wrapper around classify_step + apply_outcome.

Verifies that step() advances time and that work classified by classify_step
is reflected in the state produced by apply_outcome.
"""

from __future__ import annotations

import dataclasses

from simulation.algorithms import astar_pathfind
from simulation.domain import TaskId, Environment, Robot, RobotId, RobotState, WorkTask, SpatialConstraint, TaskState
from simulation.primitives import Position, Time
from simulation.engine_rewrite import Assignment, SimulationState
from simulation.engine_rewrite._step import step


def _base_state() -> SimulationState:
    task = WorkTask(
        id=TaskId(1),
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(0, 0), max_distance=0),
    )
    return SimulationState(
        environment=Environment(width=10, height=10),
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks={TaskId(1): task},
        task_states={TaskId(1): TaskState(task_id=TaskId(1))},
        t_now=Time(0),
    )


def test_step_advances_time():
    state = _base_state()
    new_state, _ = step(state, astar_pathfind)
    assert new_state.t_now == Time(1)


def test_step_work_is_recorded_in_new_state():
    # Robot is at the task location — classify_step produces worked,
    # apply_outcome records it: work_done should be Time(1) after one step.
    assignment = Assignment(task_id=TaskId(1), robot_id=RobotId(1))
    state = dataclasses.replace(_base_state(), assignments=(assignment,))
    new_state, _ = step(state, astar_pathfind)
    assert new_state.task_states[TaskId(1)].work_done == Time(1)
