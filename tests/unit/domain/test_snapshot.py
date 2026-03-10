import pytest
from simulation.domain.environment import Environment
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.task import Task, TaskId, TaskType
from simulation.domain.task_state import TaskState, TaskStatus
from simulation.engine.simulation import Simulation
from simulation.primitives.position import Position
from simulation.primitives.time import Time


def _make_sim() -> Simulation:
    env = Environment(width=5, height=5)
    robot = Robot(id=RobotId(1), capabilities=frozenset())
    task = Task(id=TaskId(1), type=TaskType.ROUTINE_INSPECTION, priority=1, required_work_time=Time(5))
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))
    task_state = TaskState(task_id=TaskId(1))
    return Simulation(
        environment=env,
        robots=[robot],
        tasks=[task],
        robot_states={RobotId(1): robot_state},
        task_states={TaskId(1): task_state},
    )


# ---------------------------------------------------------------------------
# Snapshot isolation from live robot state
# ---------------------------------------------------------------------------

def test_snapshot_robot_state_is_not_live():
    sim = _make_sim()
    snap = sim.snapshot()
    snap_position_before = snap.robot_states[RobotId(1)].position

    # Mutate the live robot state after the snapshot was taken
    sim.robot_states[RobotId(1)].position = Position(3, 4)

    assert snap.robot_states[RobotId(1)].position == snap_position_before


# ---------------------------------------------------------------------------
# Snapshot isolation from live task state
# ---------------------------------------------------------------------------

def test_snapshot_task_state_is_not_live():
    sim = _make_sim()
    snap = sim.snapshot()
    assert snap.task_states[TaskId(1)].status is None

    # Mutate the live task state after the snapshot was taken
    sim.task_states[TaskId(1)].status = TaskStatus.DONE

    assert snap.task_states[TaskId(1)].status is None


# ---------------------------------------------------------------------------
# Read-only dict views
# ---------------------------------------------------------------------------

def test_snapshot_dicts_are_read_only():
    sim = _make_sim()
    snap = sim.snapshot()

    with pytest.raises(TypeError):
        snap.robot_states[RobotId(1)] = None  # type: ignore[index]


# ---------------------------------------------------------------------------
# Snapshot reflects state at time of call
# ---------------------------------------------------------------------------

def test_snapshot_reflects_state_at_time_of_call():
    sim = _make_sim()

    # Set live state before snapshotting
    sim.robot_states[RobotId(1)].position = Position(2, 2)
    snap = sim.snapshot()
    assert snap.robot_states[RobotId(1)].position == Position(2, 2)

    # Mutate after snapshot — snapshot must not change
    sim.robot_states[RobotId(1)].position = Position(4, 4)
    assert snap.robot_states[RobotId(1)].position == Position(2, 2)
