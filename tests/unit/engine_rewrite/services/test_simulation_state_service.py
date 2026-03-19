from simulation.domain import RobotId, RobotState, TaskId
from simulation.domain.task_state import TaskState
from simulation.primitives import Position, Time
from simulation.engine_rewrite.services.in_memory_simulation_state_service import InMemorySimulationStateService


def _robot_state(rid: int, x: int = 0, y: int = 0) -> RobotState:
    return RobotState(robot_id=RobotId(rid), position=Position(x, y))


def _task_state(tid: int) -> TaskState:
    return TaskState(task_id=TaskId(tid))


def test_empty_by_default():
    svc = InMemorySimulationStateService()
    robot_states, task_states = svc.get_snapshot()
    assert robot_states == {}
    assert task_states == {}


def test_init_robot_appears_in_snapshot():
    svc = InMemorySimulationStateService()
    svc.init_robot(RobotId(1), _robot_state(1, x=3, y=4))
    robot_states, _ = svc.get_snapshot()
    assert RobotId(1) in robot_states
    assert robot_states[RobotId(1)].position == Position(3, 4)


def test_init_task_appears_in_snapshot():
    svc = InMemorySimulationStateService()
    svc.init_task(TaskId(1), _task_state(1))
    _, task_states = svc.get_snapshot()
    assert TaskId(1) in task_states


def test_apply_overwrites_state():
    svc = InMemorySimulationStateService()
    svc.init_robot(RobotId(1), _robot_state(1, x=0, y=0))
    new_robot_states = {RobotId(1): _robot_state(1, x=5, y=5)}
    new_task_states = {TaskId(1): _task_state(1)}
    svc.apply(new_robot_states, new_task_states)
    robot_states, task_states = svc.get_snapshot()
    assert robot_states[RobotId(1)].position == Position(5, 5)
    assert TaskId(1) in task_states


def test_get_snapshot_returns_independent_copy():
    svc = InMemorySimulationStateService()
    svc.init_robot(RobotId(1), _robot_state(1))
    robot_states, _ = svc.get_snapshot()
    # Mutating the returned dict does not affect the service
    robot_states[RobotId(99)] = _robot_state(99)
    robot_states2, _ = svc.get_snapshot()
    assert RobotId(99) not in robot_states2
