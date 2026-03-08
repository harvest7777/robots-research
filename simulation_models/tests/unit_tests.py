from simulation_models.assignment import RobotId
from simulation_models.capability import Capability
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.simulation import Simulation
from simulation_models.task import Task, TaskId, TaskType, SpatialConstraint
from simulation_models.zone import Zone, ZoneId, ZoneType
from simulation_models.task_state import TaskState, TaskStatus
from simulation_models.time import Time


# Top-right 2x2 corner of the 5x5 environment
_ZONE = Zone.from_positions(ZoneId(1), ZoneType.INSPECTION, [
    Position(3.0, 0.0), Position(4.0, 0.0),
    Position(3.0, 1.0), Position(4.0, 1.0),
])


def _create_sim_fixture() -> Simulation:
    env = Environment(width=5, height=5)
    env.add_zone(_ZONE)
    return Simulation(
        environment=env,
        robots=[],
        tasks=[],
        robot_states={},
        task_states={},
    )


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

def test_returns_robot_id_when_robot_meets_required_capabilities():
    # Arrange
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert
    assert result == [RobotId(1)]


def test_returns_robot_id_when_robot_has_superset_of_required_capabilities():
    # Arrange: task needs VISION; robot has VISION + MANIPULATION
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION, Capability.MANIPULATION}), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert
    assert result == [RobotId(1)]


def test_returns_robot_id_when_task_has_no_required_capabilities():
    # Arrange: task has no capability requirements — any robot with battery qualifies
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
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
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1), RobotId(2)})
    capable_robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1.0)
    incapable_robot = Robot(id=RobotId(2), capabilities=frozenset(), speed=1.0)

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): capable_robot, RobotId(2): incapable_robot},
        robot_states={
            RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0)),
            RobotId(2): RobotState(robot_id=RobotId(2), position=Position(0.0, 0.0)),
        },
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert: only the capable robot is returned; incapable robot is excluded
    assert result == [RobotId(1)]


def test_returns_empty_when_no_robot_meets_required_capabilities():
    # Arrange
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert
    assert result == []


# ---------------------------------------------------------------------------
# Battery
# ---------------------------------------------------------------------------

def test_returns_empty_when_robot_has_no_battery():
    # Arrange
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0), battery_level=0.0)

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert
    assert result == []


# ---------------------------------------------------------------------------
# Task terminal status
# ---------------------------------------------------------------------------

def test_returns_empty_when_task_is_failed():
    # Arrange
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.FAILED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
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
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.DONE, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert
    assert result == []


def test_returns_empty_when_no_robots_are_assigned():
    # Arrange
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.UNASSIGNED, assigned_robot_ids=set())

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={},
        robot_states={},
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert
    assert result == []


# ---------------------------------------------------------------------------
# Deadline
# ---------------------------------------------------------------------------

def test_returns_empty_when_deadline_has_passed():
    # Arrange: task deadline is tick 5, current time is tick 6
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        deadline=Time(5),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(6),
    )

    # Assert
    assert result == []


def test_returns_robot_id_when_time_equals_deadline():
    # Arrange: time == deadline — boundary, should still be workable
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        deadline=Time(5),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(5),
    )

    # Assert
    assert result == [RobotId(1)]


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def test_returns_empty_when_dependency_is_not_done():
    # Arrange: task depends on task 2, which is still IN_PROGRESS
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        dependencies=frozenset({TaskId(2)}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    dep_state = TaskState(task_id=TaskId(2), status=TaskStatus.IN_PROGRESS)
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state, TaskId(2): dep_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert
    assert result == []


def test_returns_robot_id_when_all_dependencies_are_done():
    # Arrange: task depends on task 2, which is DONE
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        dependencies=frozenset({TaskId(2)}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    dep_state = TaskState(task_id=TaskId(2), status=TaskStatus.DONE)
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state, TaskId(2): dep_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert
    assert result == [RobotId(1)]


# ---------------------------------------------------------------------------
# Multiple robots
# ---------------------------------------------------------------------------

def test_returns_all_robot_ids_when_multiple_robots_are_eligible():
    # Arrange: two robots, both fully qualified
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1), RobotId(2)})

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={
            RobotId(1): Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0),
            RobotId(2): Robot(id=RobotId(2), capabilities=frozenset(), speed=1.0),
        },
        robot_states={
            RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0)),
            RobotId(2): RobotState(robot_id=RobotId(2), position=Position(0.0, 0.0)),
        },
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert: order not guaranteed since assigned_robot_ids is a set
    assert set(result) == {RobotId(1), RobotId(2)}


# ---------------------------------------------------------------------------
# Spatial constraint — Position target
# ---------------------------------------------------------------------------

def test_returns_empty_when_robot_is_outside_spatial_constraint():
    # Arrange: task requires robot to be at (10, 10); robot is at (0, 0)
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=Position(10.0, 10.0), max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert
    assert result == []


def test_returns_robot_id_when_robot_is_within_position_max_distance():
    # Arrange: task target is (0, 0), max_distance=2; robot is 1.5 units away
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=Position(0.0, 0.0), max_distance=2),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(1.5, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert
    assert result == [RobotId(1)]


def test_returns_empty_when_robot_is_just_outside_position_max_distance():
    # Arrange: task target is (0, 0), max_distance=1; robot is 2.0 units away
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=Position(0.0, 0.0), max_distance=1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(2.0, 0.0))

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    )

    # Assert
    assert result == []


# ---------------------------------------------------------------------------
# Spatial constraint — Zone target  (⚠ zone check not yet implemented)
# ---------------------------------------------------------------------------

def test_returns_robot_id_when_robot_is_in_zone_with_required_capabilities():
    # Arrange: robot positioned inside _ZONE at cell (4, 0)
    sim = _create_sim_fixture()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(4.5, 0.5))  # floors to cell (4, 0)

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=sim.environment,
        time=Time(0),
    )

    # Assert
    assert result == [RobotId(1)]


def test_returns_empty_when_robot_has_capabilities_but_is_outside_required_zone():
    # Arrange: robot at (0, 0) — outside _ZONE (top-right corner)
    sim = _create_sim_fixture()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0.0, 0.0))  # outside zone

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=sim.environment,
        time=Time(0),
    )

    # Assert
    assert result == []


def test_returns_robot_id_when_robot_is_in_zone_no_capabilities_required():
    # Arrange: robot inside _ZONE, task has no capability requirement
    sim = _create_sim_fixture()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(3.5, 0.5))  # floors to cell (3, 0)

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=sim.environment,
        time=Time(0),
    )

    # Assert
    assert result == [RobotId(1)]


def test_returns_empty_when_robot_is_in_zone_but_missing_capabilities():
    # Arrange: robot inside _ZONE but lacks required capability
    sim = _create_sim_fixture()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(3.5, 0.5))  # floors to cell (3, 0)

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=sim.environment,
        time=Time(0),
    )

    # Assert
    assert result == []


def test_returns_only_in_zone_robot_ids_when_robots_have_mixed_zone_positions():
    # Arrange: two robots with caps; robot 1 inside _ZONE, robot 2 outside
    sim = _create_sim_fixture()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1), RobotId(2)})

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={
            RobotId(1): Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1.0),
            RobotId(2): Robot(id=RobotId(2), capabilities=frozenset({Capability.VISION}), speed=1.0),
        },
        robot_states={
            RobotId(1): RobotState(robot_id=RobotId(1), position=Position(3.5, 0.5)),  # in zone
            RobotId(2): RobotState(robot_id=RobotId(2), position=Position(0.0, 0.0)),  # outside zone
        },
        environment=sim.environment,
        time=Time(0),
    )

    # Assert
    assert result == [RobotId(1)]


def test_returns_robot_id_when_robot_is_within_zone_max_distance():
    # Arrange: robot at (2.5, 0.5), ~0.7 units from nearest zone cell (3, 0); max_distance=1
    sim = _create_sim_fixture()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(2.5, 0.5))  # ~0.7 from cell (3, 0)

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=sim.environment,
        time=Time(0),
    )

    # Assert
    assert result == [RobotId(1)]


def test_returns_empty_when_robot_exceeds_zone_max_distance():
    # Arrange: robot at (1.0, 0.0), 2.0 units from nearest zone cell (3, 0); max_distance=1
    sim = _create_sim_fixture()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(1.0, 0.0))  # 2.0 from cell (3, 0)

    # Act
    result = Simulation._get_eligible_robot_ids_for_task(
        task,
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=sim.environment,
        time=Time(0),
    )

    # Assert
    assert result == []
