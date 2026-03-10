from simulation_models.robot_state import RobotId
from simulation_models.capability import Capability
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.step_context import StepContext
from simulation_models.task import Task, TaskId, TaskType, SpatialConstraint
from simulation_models.zone import Zone, ZoneId, ZoneType
from simulation_models.task_state import TaskState, TaskStatus
from simulation_models.time import Time
from simulation_models.work_eligibility import get_eligible_robots


def _ctx(
    task_states: dict,
    robots: dict,
    robot_states: dict,
    environment: Environment,
    time: Time,
) -> StepContext:
    return StepContext(
        robot_states=robot_states,
        task_states=task_states,
        robot_to_task={},
        robot_by_id=robots,
        task_by_id={},
        environment=environment,
        t_now=time,
    )


# Top-right 2x2 corner of the 5x5 environment
_ZONE = Zone.from_positions(ZoneId(1), ZoneType.INSPECTION, [
    Position(3, 0), Position(4, 0),
    Position(3, 1), Position(4, 1),
])


def _env_with_zone() -> "Environment":
    env = Environment(width=5, height=5)
    env.add_zone(_ZONE)
    return env


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

def test_returns_robot_id_when_robot_meets_required_capabilities():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == [RobotId(1)]


def test_returns_robot_id_when_robot_has_superset_of_required_capabilities():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION, Capability.MANIPULATION}), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == [RobotId(1)]


def test_returns_robot_id_when_task_has_no_required_capabilities():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == [RobotId(1)]


def test_returns_only_capable_robot_ids_when_robots_have_mixed_capabilities():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1), RobotId(2)})
    capable_robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1)
    incapable_robot = Robot(id=RobotId(2), capabilities=frozenset(), speed=1)

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): capable_robot, RobotId(2): incapable_robot},
        robot_states={
            RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0)),
            RobotId(2): RobotState(robot_id=RobotId(2), position=Position(0, 0)),
        },
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == [RobotId(1)]


def test_returns_empty_when_no_robot_meets_required_capabilities():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == []


# ---------------------------------------------------------------------------
# Battery
# ---------------------------------------------------------------------------

def test_returns_empty_when_robot_has_no_battery():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0), battery_level=0.0)

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == []


# ---------------------------------------------------------------------------
# Task terminal status
# ---------------------------------------------------------------------------

def test_returns_empty_when_task_is_failed():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.FAILED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == []


def test_returns_empty_when_task_is_completed():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.DONE, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == []


def test_returns_empty_when_no_robots_are_assigned():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.UNASSIGNED, assigned_robot_ids=set())

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={},
        robot_states={},
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == []


# ---------------------------------------------------------------------------
# Deadline
# ---------------------------------------------------------------------------

def test_returns_empty_when_deadline_has_passed():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        deadline=Time(5),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(6),
    ))

    assert result == []


def test_returns_robot_id_when_time_equals_deadline():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        deadline=Time(5),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(5),
    ))

    assert result == [RobotId(1)]


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def test_returns_empty_when_dependency_is_not_done():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        dependencies=frozenset({TaskId(2)}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    dep_state = TaskState(task_id=TaskId(2), status=TaskStatus.IN_PROGRESS)
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state, TaskId(2): dep_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == []


def test_returns_robot_id_when_all_dependencies_are_done():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        dependencies=frozenset({TaskId(2)}),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    dep_state = TaskState(task_id=TaskId(2), status=TaskStatus.DONE)
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state, TaskId(2): dep_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == [RobotId(1)]


# ---------------------------------------------------------------------------
# Multiple robots
# ---------------------------------------------------------------------------

def test_returns_all_robot_ids_when_multiple_robots_are_eligible():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1), RobotId(2)})

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={
            RobotId(1): Robot(id=RobotId(1), capabilities=frozenset(), speed=1),
            RobotId(2): Robot(id=RobotId(2), capabilities=frozenset(), speed=1),
        },
        robot_states={
            RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0)),
            RobotId(2): RobotState(robot_id=RobotId(2), position=Position(0, 0)),
        },
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert set(result) == {RobotId(1), RobotId(2)}


# ---------------------------------------------------------------------------
# Spatial constraint — Position target
# ---------------------------------------------------------------------------

def test_returns_empty_when_robot_is_outside_spatial_constraint():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=Position(10, 10), max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=1, height=1),
        time=Time(0),
    ))

    assert result == []


def test_returns_robot_id_when_robot_is_at_position_target():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=Position(2, 3), max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(2, 3))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=5, height=5),
        time=Time(0),
    ))

    assert result == [RobotId(1)]


def test_returns_empty_when_robot_is_one_cell_away_from_exact_target():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=Position(0, 0), max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(1, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=5, height=5),
        time=Time(0),
    ))

    assert result == []


def test_returns_robot_id_when_robot_is_within_position_max_distance():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=Position(0, 0), max_distance=2),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(1, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=5, height=5),
        time=Time(0),
    ))

    assert result == [RobotId(1)]


def test_returns_empty_when_robot_is_just_outside_position_max_distance():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=Position(0, 0), max_distance=1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(2, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=Environment(width=5, height=5),
        time=Time(0),
    ))

    assert result == []


# ---------------------------------------------------------------------------
# Spatial constraint — Zone target
# ---------------------------------------------------------------------------

def test_returns_robot_id_when_robot_is_in_zone_with_required_capabilities():
    env = _env_with_zone()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(4, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=env,
        time=Time(0),
    ))

    assert result == [RobotId(1)]


def test_returns_empty_when_robot_has_capabilities_but_is_outside_required_zone():
    env = _env_with_zone()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(0, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=env,
        time=Time(0),
    ))

    assert result == []


def test_returns_robot_id_when_robot_is_in_zone_no_capabilities_required():
    env = _env_with_zone()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(3, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=env,
        time=Time(0),
    ))

    assert result == [RobotId(1)]


def test_returns_empty_when_robot_is_in_zone_but_missing_capabilities():
    env = _env_with_zone()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(3, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=env,
        time=Time(0),
    ))

    assert result == []


def test_returns_only_in_zone_robot_ids_when_robots_have_mixed_zone_positions():
    env = _env_with_zone()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        required_capabilities=frozenset({Capability.VISION}),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=0),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1), RobotId(2)})

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={
            RobotId(1): Robot(id=RobotId(1), capabilities=frozenset({Capability.VISION}), speed=1),
            RobotId(2): Robot(id=RobotId(2), capabilities=frozenset({Capability.VISION}), speed=1),
        },
        robot_states={
            RobotId(1): RobotState(robot_id=RobotId(1), position=Position(3, 0)),
            RobotId(2): RobotState(robot_id=RobotId(2), position=Position(0, 0)),
        },
        environment=env,
        time=Time(0),
    ))

    assert result == [RobotId(1)]


def test_returns_robot_id_when_robot_is_within_zone_max_distance():
    env = _env_with_zone()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(2, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=env,
        time=Time(0),
    ))

    assert result == [RobotId(1)]


def test_returns_empty_when_robot_exceeds_zone_max_distance():
    env = _env_with_zone()
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=_ZONE.id, max_distance=1),
    )
    task_state = TaskState(task_id=TaskId(1), status=TaskStatus.ASSIGNED, assigned_robot_ids={RobotId(1)})
    robot = Robot(id=RobotId(1), capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=RobotId(1), position=Position(1, 0))

    result = get_eligible_robots(task, _ctx(
        task_states={TaskId(1): task_state},
        robots={RobotId(1): robot},
        robot_states={RobotId(1): robot_state},
        environment=env,
        time=Time(0),
    ))

    assert result == []
