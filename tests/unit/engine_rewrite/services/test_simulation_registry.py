from simulation.domain import Robot, RobotId, WorkTask, SpatialConstraint, TaskId
from simulation.primitives import Position, Time
from simulation.engine_rewrite.services import InMemorySimulationRegistry


def _task(tid: int) -> WorkTask:
    return WorkTask(
        id=TaskId(tid),
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(0, 0)),
    )


def _robot(rid: int) -> Robot:
    return Robot(id=RobotId(rid), capabilities=frozenset())


def test_empty_by_default():
    reg = InMemorySimulationRegistry()
    assert reg.all_tasks() == []
    assert reg.all_robots() == []


def test_constructor_accepts_initial_tasks_and_robots():
    reg = InMemorySimulationRegistry(tasks=[_task(1)], robots=[_robot(1)])
    assert len(reg.all_tasks()) == 1
    assert len(reg.all_robots()) == 1


def test_add_and_get_task():
    reg = InMemorySimulationRegistry()
    reg.add_task(_task(1))
    assert reg.get_task(TaskId(1)) is not None


def test_get_task_returns_none_when_missing():
    reg = InMemorySimulationRegistry()
    assert reg.get_task(TaskId(99)) is None


def test_add_task_overwrites_existing():
    t1 = _task(1)
    t2 = WorkTask(
        id=TaskId(1),
        priority=99,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=Position(0, 0)),
    )
    reg = InMemorySimulationRegistry(tasks=[t1])
    reg.add_task(t2)
    assert reg.get_task(TaskId(1)).priority == 99


def test_all_tasks_returns_all():
    reg = InMemorySimulationRegistry(tasks=[_task(1), _task(2), _task(3)])
    assert len(reg.all_tasks()) == 3


def test_add_and_get_robot():
    reg = InMemorySimulationRegistry()
    reg.add_robot(_robot(1))
    assert reg.get_robot(RobotId(1)) is not None


def test_get_robot_returns_none_when_missing():
    reg = InMemorySimulationRegistry()
    assert reg.get_robot(RobotId(99)) is None


def test_add_robot_overwrites_existing():
    from simulation.primitives import Capability
    r1 = _robot(1)
    r2 = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}))
    reg = InMemorySimulationRegistry(robots=[r1])
    reg.add_robot(r2)
    assert reg.get_robot(RobotId(1)).capabilities == frozenset({Capability.VISION})


def test_all_robots_returns_all():
    reg = InMemorySimulationRegistry(robots=[_robot(1), _robot(2)])
    assert len(reg.all_robots()) == 2
