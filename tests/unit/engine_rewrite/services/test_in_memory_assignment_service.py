from simulation.domain.base_task import TaskId
from simulation.domain.robot_state import RobotId
from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.services.in_memory_assignment_service import InMemoryAssignmentService


def _assign(robot_id: int, task_id: int) -> Assignment:
    return Assignment(task_id=TaskId(task_id), robot_id=RobotId(robot_id))


def test_empty_by_default():
    assert InMemoryAssignmentService().get_current() == []


def test_set_replaces_assignments():
    service = InMemoryAssignmentService()
    service.set([_assign(1, 10), _assign(2, 20)])
    assert set(service.get_current()) == {_assign(1, 10), _assign(2, 20)}


def test_set_overwrites_previous():
    service = InMemoryAssignmentService()
    service.set([_assign(1, 10)])
    service.set([_assign(2, 20)])
    assert service.get_current() == [_assign(2, 20)]


def test_set_empty_clears_assignments():
    service = InMemoryAssignmentService(assignments=[_assign(1, 10)])
    service.set([])
    assert service.get_current() == []


def test_constructor_accepts_initial_assignments():
    service = InMemoryAssignmentService(assignments=[_assign(1, 10)])
    assert service.get_current() == [_assign(1, 10)]
