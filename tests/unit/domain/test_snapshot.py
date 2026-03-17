import dataclasses
from types import MappingProxyType

import pytest
from simulation.domain.environment import Environment
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.task import TaskId
from simulation.domain.task_state import TaskState
from simulation.engine.snapshot import SimulationSnapshot
from simulation.primitives.position import Position
from simulation.primitives.time import Time


def _snap(robot_state: RobotState, task_state: TaskState) -> SimulationSnapshot:
    return SimulationSnapshot(
        env=Environment(width=5, height=5),
        robots=(),
        robot_states=MappingProxyType({robot_state.robot_id: dataclasses.replace(robot_state)}),
        tasks=(),
        task_states=MappingProxyType({task_state.task_id: dataclasses.replace(task_state)}),
        t_now=Time(0),
    )


# ---------------------------------------------------------------------------
# Snapshot isolation from live robot state
# ---------------------------------------------------------------------------

def test_snapshot_captures_robot_state_at_creation():
    # RobotState is frozen — mutation is impossible; snapshot reflects creation-time values.
    live = RobotState(robot_id=RobotId(1), position=Position(0, 0))
    snap = _snap(live, TaskState(task_id=TaskId(1)))

    assert snap.robot_states[RobotId(1)].position == Position(0, 0)


# ---------------------------------------------------------------------------
# Snapshot isolation from live task state
# ---------------------------------------------------------------------------

def test_snapshot_captures_task_state_at_creation():
    # TaskState is frozen — mutation is impossible; snapshot reflects creation-time values.
    live = TaskState(task_id=TaskId(1))
    snap = _snap(RobotState(robot_id=RobotId(1), position=Position(0, 0)), live)

    assert snap.task_states[TaskId(1)].status is None


# ---------------------------------------------------------------------------
# Read-only dict views
# ---------------------------------------------------------------------------

def test_snapshot_dicts_are_read_only():
    snap = _snap(
        RobotState(robot_id=RobotId(1), position=Position(0, 0)),
        TaskState(task_id=TaskId(1)),
    )

    with pytest.raises(TypeError):
        snap.robot_states[RobotId(1)] = None  # type: ignore[index]


# ---------------------------------------------------------------------------
# Snapshot reflects state at time of call
# ---------------------------------------------------------------------------

def test_snapshot_reflects_state_at_time_of_call():
    live = RobotState(robot_id=RobotId(1), position=Position(2, 2))
    snap = _snap(live, TaskState(task_id=TaskId(1)))

    assert snap.robot_states[RobotId(1)].position == Position(2, 2)
