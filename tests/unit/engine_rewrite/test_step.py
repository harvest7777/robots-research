"""
Smoke tests for step() — the thin wrapper around classify_step + apply_outcome.

Confirms the two-function pipeline is wired correctly and that step() returns
the right types with the expected relationship between inputs and outputs.
"""

from __future__ import annotations

from simulation.algorithms.astar_pathfinding import astar_pathfind
from simulation.domain.base_task import TaskId
from simulation.domain.environment import Environment
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.task import Task, TaskType, SpatialConstraint
from simulation.domain.task_state import TaskState
from simulation.primitives.position import Position
from simulation.primitives.time import Time

from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.simulation_state import SimulationState
from simulation.engine_rewrite.step import step
from simulation.engine_rewrite.step_outcome import StepOutcome


def _base_state() -> SimulationState:
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
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


def test_step_returns_new_state_and_outcome():
    state = _base_state()
    new_state, outcome = step(state, [], astar_pathfind)
    assert new_state is not state
    assert isinstance(outcome, StepOutcome)


def test_step_advances_time():
    state = _base_state()
    new_state, _ = step(state, [], astar_pathfind)
    assert new_state.t_now == Time(1)


def test_step_does_not_mutate_input_state():
    state = _base_state()
    original_t = state.t_now
    step(state, [], astar_pathfind)
    assert state.t_now == original_t


def test_step_threads_classify_into_apply():
    # Robot is at the task location — classify_step should produce worked,
    # apply_outcome should record work progress on the task state.
    state = _base_state()
    assignment = Assignment(task_id=TaskId(1), robot_id=RobotId(1))
    new_state, outcome = step(state, [assignment], astar_pathfind)
    assert (RobotId(1), TaskId(1)) in outcome.worked
    ts = new_state.task_states[TaskId(1)]
    assert isinstance(ts, TaskState)
    assert ts.work_done == Time(1)
