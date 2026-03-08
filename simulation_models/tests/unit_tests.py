from simulation_models.assignment import RobotId
from simulation_models.capability import Capability
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.simulation import Simulation
from simulation_models.task import Task, TaskId, TaskType, SpatialConstraint
from simulation_models.task_state import TaskState, TaskStatus
from simulation_models.time import Time


def _create_sim_fixture() -> Simulation:
    return Simulation(
        environment=Environment(width=1, height=1),
        robots=[],
        tasks=[],
        robot_states={},
        task_states={},
    )


def test_returns_robot_id_when_robot_meets_required_capabilities():
    # Arrange
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED)
    robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._task_can_be_worked_on(
        task,
        task_state,
        assigned_robots=[(robot, robot_state)],
        time=Time(0),
    )

    # Assert
    assert result == [RobotId(1)]


def test_returns_only_capable_robot_ids_when_robots_have_mixed_capabilities():
    # Arrange: task requires VISION; one capable robot, one without
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED)
    capable_robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1.0)
    incapable_robot = Robot(id=RobotId(2), capabilities=frozenset(), speed=1.0)
    capable_robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))
    incapable_robot_state = RobotState(robot_id=RobotId(2), position=Position(0.0, 0.0))

    # Act
    result = Simulation._task_can_be_worked_on(
        task,
        task_state,
        assigned_robots=[(capable_robot, capable_robot_state), (incapable_robot, incapable_robot_state)],
        time=Time(0),
    )

    # Assert: only the capable robot is returned; incapable robot is excluded
    assert result == [RobotId(1)]


def test_returns_empty_when_robot_has_no_battery():
    # Arrange
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED)
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0), battery_level=0.0)

    # Act
    result = Simulation._task_can_be_worked_on(
        task,
        task_state,
        assigned_robots=[(robot, robot_state)],
        time=Time(0),
    )

    # Assert
    assert result == []


def test_returns_empty_when_task_is_failed():
    # Arrange
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.FAILED)
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._task_can_be_worked_on(
        task,
        task_state,
        assigned_robots=[(robot, robot_state)],
        time=Time(0),
    )

    # Assert
    assert result == []


def test_returns_empty_when_task_is_completed():
    # Arrange
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.DONE)
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._task_can_be_worked_on(
        task,
        task_state,
        assigned_robots=[(robot, robot_state)],
        time=Time(0),
    )

    # Assert
    assert result == []


def test_returns_empty_when_robot_is_outside_spatial_constraint():
    # Arrange: task requires robot to be at (10, 10); robot is at (0, 0)
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=Position(10.0, 10.0), max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED)
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._task_can_be_worked_on(
        task,
        task_state,
        assigned_robots=[(robot, robot_state)],
        time=Time(0),
    )

    # Assert
    assert result == []


def test_returns_empty_when_no_robot_meets_required_capabilities():
    # Arrange
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED)
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._task_can_be_worked_on(
        task,
        task_state,
        assigned_robots=[(robot, robot_state)],
        time=Time(0),
    )

    # Assert
    assert result == []


def test_returns_empty_when_deadline_has_passed():
    # Arrange: task deadline is tick 5, current time is tick 6
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        deadline=Time(5),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED)
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._task_can_be_worked_on(
        task,
        task_state,
        assigned_robots=[(robot, robot_state)],
        time=Time(6),
    )

    # Assert
    assert result == []
