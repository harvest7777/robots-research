from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.task import Task, TaskId, TaskType, SpatialConstraint
from simulation_models.time import Time
from simulation_models.zone import Zone, ZoneId, ZoneType
from simulation_models.movement_planner import resolve_task_target_position


# ---------------------------------------------------------------------------
# resolve_task_target_position
# ---------------------------------------------------------------------------

def test_returns_none_when_task_has_no_spatial_constraint():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    result = resolve_task_target_position(task, Position(0, 0), Environment(width=5, height=5))
    assert result is None


def test_returns_position_target_directly():
    target = Position(3, 4)
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=target),
    )
    result = resolve_task_target_position(task, Position(0, 0), Environment(width=5, height=5))
    assert result == target


def test_returns_none_when_zone_id_not_found_in_environment():
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=ZoneId(99)),
    )
    result = resolve_task_target_position(task, Position(0, 0), Environment(width=5, height=5))
    assert result is None


def test_returns_nearest_zone_cell_to_robot():
    # Zone spans x=3..4, y=0..1 — robot at (0, 0) is closest to (3, 0)
    zone = Zone.from_positions(ZoneId(1), ZoneType.INSPECTION, [
        Position(3, 0), Position(4, 0),
        Position(3, 1), Position(4, 1),
    ])
    env = Environment(width=5, height=5)
    env.add_zone(zone)
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=ZoneId(1)),
    )

    result = resolve_task_target_position(task, Position(0, 0), env)

    assert result == Position(3, 0)


def test_returns_correct_nearest_cell_when_robot_is_adjacent_to_different_corner():
    # Same zone, robot at (4, 4) is closest to (4, 1)
    zone = Zone.from_positions(ZoneId(1), ZoneType.INSPECTION, [
        Position(3, 0), Position(4, 0),
        Position(3, 1), Position(4, 1),
    ])
    env = Environment(width=5, height=5)
    env.add_zone(zone)
    task = Task(
        id=TaskId(1),
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(target=ZoneId(1)),
    )

    result = resolve_task_target_position(task, Position(4, 4), env)

    assert result == Position(4, 1)
