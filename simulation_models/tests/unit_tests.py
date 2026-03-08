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


def test_task_can_be_worked_on_if_at_least_one_robot_meets_required_capabilities():
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
    assert result == [(robot, robot_state)]


def test_task_is_only_worked_on_by_robots_with_required_capabilities():
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
    assert result == [(capable_robot, capable_robot_state)]


def test_task_can_not_be_worked_on_if_robot_is_out_of_battery():
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


def test_failed_task_can_not_be_worked_on():
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


def test_completed_task_can_not_be_worked_on():
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


def task_can_not_be_worked_on_if_robots_are_not_within_spatial_constraint():
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


def test_task_can_not_be_worked_on_if_no_robot_has_the_required_capabilities():
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
