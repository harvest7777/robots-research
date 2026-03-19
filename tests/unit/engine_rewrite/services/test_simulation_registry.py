from simulation.domain import RobotId, RobotState, WorkTask, SpatialConstraint, TaskId
from simulation.domain.robot import Robot
from simulation.domain.task_state import TaskState
from simulation.primitives import Capability, Position, Time
from simulation.engine_rewrite.services import InMemorySimulationStore


def _task(tid: int) -> WorkTask:
    return WorkTask(
        id=TaskId(tid),
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(0, 0)),
    )


def _robot(rid: int) -> Robot:
    return Robot(id=RobotId(rid), capabilities=frozenset())


def _state(rid: int) -> RobotState:
    return RobotState(robot_id=RobotId(rid), position=Position(0, 0))


def _task_state(tid: int) -> TaskState:
    return TaskState(task_id=TaskId(tid))


def test_empty_by_default():
    store = InMemorySimulationStore()
    assert store.all_tasks() == []
    assert store.all_robots() == []


def test_add_and_list_task():
    store = InMemorySimulationStore()
    store.add_task(_task(1), _task_state(1))
    assert len(store.all_tasks()) == 1
    assert store.all_tasks()[0].id == TaskId(1)


def test_add_and_list_robot():
    store = InMemorySimulationStore()
    store.add_robot(_robot(1), _state(1))
    assert len(store.all_robots()) == 1
    assert store.all_robots()[0].id == RobotId(1)


def test_add_task_overwrites_existing():
    t2 = WorkTask(
        id=TaskId(1),
        priority=99,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=Position(0, 0)),
    )
    store = InMemorySimulationStore()
    store.add_task(_task(1), _task_state(1))
    store.add_task(t2, _task_state(1))
    assert store.all_tasks()[0].priority == 99


def test_add_robot_overwrites_existing():
    r2 = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}))
    store = InMemorySimulationStore()
    store.add_robot(_robot(1), _state(1))
    store.add_robot(r2, _state(1))
    assert store.all_robots()[0].capabilities == frozenset({Capability.VISION})


def test_snapshot_contains_added_state():
    store = InMemorySimulationStore()
    store.add_robot(_robot(1), RobotState(robot_id=RobotId(1), position=Position(3, 4)))
    store.add_task(_task(1), _task_state(1))
    robot_states, task_states = store.get_snapshot()
    assert robot_states[RobotId(1)].position == Position(3, 4)
    assert TaskId(1) in task_states


def test_apply_overwrites_snapshot():
    store = InMemorySimulationStore()
    store.add_robot(_robot(1), _state(1))
    new_states = {RobotId(1): RobotState(robot_id=RobotId(1), position=Position(5, 5))}
    store.apply(new_states, {})
    robot_states, _ = store.get_snapshot()
    assert robot_states[RobotId(1)].position == Position(5, 5)


def test_get_snapshot_returns_independent_copy():
    store = InMemorySimulationStore()
    store.add_robot(_robot(1), _state(1))
    robot_states, _ = store.get_snapshot()
    robot_states[RobotId(99)] = _state(99)
    robot_states2, _ = store.get_snapshot()
    assert RobotId(99) not in robot_states2
