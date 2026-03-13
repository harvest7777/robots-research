from simulation.algorithms.simple_assignment import simple_assign
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId
from simulation.domain.task import Task, TaskId, TaskType
from simulation.primitives.capability import Capability
from simulation.primitives.time import Time


def _robot(robot_id: int, *caps: Capability) -> Robot:
    return Robot(id=RobotId(robot_id), capabilities=frozenset(caps))


def _task(task_id: int, task_type: TaskType, *caps: Capability) -> Task:
    return Task(
        id=TaskId(task_id),
        type=task_type,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset(caps),
    )


# ---------------------------------------------------------------------------
# Capability matching
# ---------------------------------------------------------------------------

def test_assigns_capable_robot_to_task():
    task = _task(1, TaskType.ROUTINE_INSPECTION, Capability.MANIPULATION)
    capable = _robot(1, Capability.MANIPULATION)
    incapable = _robot(2, Capability.VISION)

    result = simple_assign([task], [capable, incapable])

    assert len(result) == 1
    assert result[0].task_id == TaskId(1)
    assert RobotId(1) in result[0].robot_ids
    assert RobotId(2) not in result[0].robot_ids


def test_multi_capability_partial_match_is_rejected():
    task = _task(1, TaskType.ROUTINE_INSPECTION, Capability.VISION, Capability.MANIPULATION)
    partial = _robot(1, Capability.VISION)
    full = _robot(2, Capability.VISION, Capability.MANIPULATION)

    result = simple_assign([task], [partial, full])

    assert len(result) == 1
    assert RobotId(2) in result[0].robot_ids
    assert RobotId(1) not in result[0].robot_ids


def test_no_capable_robot_returns_empty():
    task = _task(1, TaskType.ROUTINE_INSPECTION, Capability.REPAIR)
    robot = _robot(1, Capability.VISION)

    result = simple_assign([task], [robot])

    assert result == []

def test_does_not_double_assign_robot():
    task1 = _task(1, TaskType.ROUTINE_INSPECTION, Capability.MANIPULATION)
    task2 = _task(2, TaskType.ROUTINE_INSPECTION, Capability.MANIPULATION)
    robot = _robot(1, Capability.MANIPULATION)

    result = simple_assign([task1, task2], [robot])

    assigned_robot_ids = [rid for a in result for rid in a.robot_ids]
    assert assigned_robot_ids.count(RobotId(1)) == 1


def test_rescue_task_is_skipped():
    rescue = _task(1, TaskType.RESCUE, Capability.MANIPULATION)
    robot = _robot(1, Capability.MANIPULATION)

    result = simple_assign([rescue], [robot])

    assert result == []


def test_idle_task_is_skipped():
    idle = _task(1, TaskType.IDLE)
    robot = _robot(1, Capability.MANIPULATION)

    result = simple_assign([idle], [robot])

    assert result == []


def test_idle_task_does_not_consume_robots():
    idle = _task(1, TaskType.IDLE)
    work = _task(2, TaskType.ROUTINE_INSPECTION, Capability.MANIPULATION)
    robot = _robot(1, Capability.MANIPULATION)

    result = simple_assign([idle, work], [robot])

    assert len(result) == 1
    assert result[0].task_id == TaskId(2)


def test_search_task_gets_all_capable_robots():
    search = _task(1, TaskType.SEARCH, Capability.VISION)
    r1 = _robot(1, Capability.VISION)
    r2 = _robot(2, Capability.VISION)
    r3 = _robot(3, Capability.MANIPULATION)  # incapable

    result = simple_assign([search], [r1, r2, r3])

    assert len(result) == 1
    assert result[0].task_id == TaskId(1)
    assert result[0].robot_ids == frozenset([RobotId(1), RobotId(2)])


def test_search_with_no_capable_robots_returns_empty():
    search = _task(1, TaskType.SEARCH, Capability.MANIPULATION)
    robot = _robot(1, Capability.VISION)

    result = simple_assign([search], [robot])

    assert result == []

def test_returns_one_assignment_per_task():
    task1 = _task(1, TaskType.ROUTINE_INSPECTION, Capability.VISION)
    task2 = _task(2, TaskType.ROUTINE_INSPECTION, Capability.VISION)
    r1 = _robot(1, Capability.VISION)
    r2 = _robot(2, Capability.VISION)

    result = simple_assign([task1, task2], [r1, r2])

    task_ids = [a.task_id for a in result]
    assert len(task_ids) == len(set(task_ids))

def test_returns_multiple_eligible_robots_per_task():
    task1 = _task(1, TaskType.ROUTINE_INSPECTION, Capability.VISION)
    r1 = _robot(1, Capability.VISION)
    r2 = _robot(2, Capability.VISION)

    result = simple_assign([task1], [r1, r2])
    assert len(result[0].robot_ids) == 2
