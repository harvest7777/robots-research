from simulation.domain import TaskId, RobotId
from simulation.engine_rewrite import Assignment
from simulation.engine_rewrite.services import InMemoryAssignmentService


def _assign(robot_id: int, task_id: int) -> Assignment:
    return Assignment(task_id=TaskId(task_id), robot_id=RobotId(robot_id))


def test_empty_by_default():
    assert InMemoryAssignmentService().get_current() == []


def test_constructor_accepts_initial_assignments():
    service = InMemoryAssignmentService(assignments=[_assign(1, 10), _assign(2, 20)])
    assert set(service.get_current()) == {_assign(1, 10), _assign(2, 20)}


def test_update_adds_new_assignments():
    service = InMemoryAssignmentService()
    service.update([_assign(1, 10), _assign(2, 20)])
    assert set(service.get_current()) == {_assign(1, 10), _assign(2, 20)}


def test_update_upserts_existing_robot():
    service = InMemoryAssignmentService(assignments=[_assign(1, 10)])
    service.update([_assign(1, 99)])
    assert service.get_current() == [_assign(1, 99)]


def test_update_leaves_unmentioned_robots_unchanged():
    service = InMemoryAssignmentService(assignments=[_assign(1, 10), _assign(2, 20)])
    service.update([_assign(1, 99)])
    assert set(service.get_current()) == {_assign(1, 99), _assign(2, 20)}
