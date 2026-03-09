from simulation_models.assignment import RobotId
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.task import Task, TaskId, TaskType, SpatialConstraint
from simulation_models.time import Time
from simulation_models.zone import Zone, ZoneId, ZoneType
from simulation_models.movement_planner import resolve_collisions, resolve_task_target_position


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


# ---------------------------------------------------------------------------
# resolve_collisions
# ---------------------------------------------------------------------------

def test_resolve_collisions_no_conflict_passes_through():
    # R1 moves to (1, 0), R2 moves to (2, 0) — no overlap
    planned = {RobotId(1): Position(1, 0), RobotId(2): Position(2, 0)}
    current = {RobotId(1): Position(0, 0), RobotId(2): Position(1, 0)}

    result = resolve_collisions(planned, current)

    assert result == {RobotId(1): Position(1, 0), RobotId(2): Position(2, 0)}


def test_resolve_collisions_none_moves_pass_through():
    # Both robots have no planned move — should stay as None
    planned = {RobotId(1): None, RobotId(2): None}
    current = {RobotId(1): Position(0, 0), RobotId(2): Position(1, 0)}

    result = resolve_collisions(planned, current)

    assert result == {RobotId(1): None, RobotId(2): None}


def test_resolve_collisions_stayer_blocks_incoming_mover():
    # R1 stays at (1, 0); R2 tries to move to (1, 0) — R2 should be cancelled
    planned = {RobotId(1): None, RobotId(2): Position(1, 0)}
    current = {RobotId(1): Position(1, 0), RobotId(2): Position(0, 0)}

    result = resolve_collisions(planned, current)

    assert result[RobotId(1)] is None
    assert result[RobotId(2)] is None


def test_resolve_collisions_two_movers_to_same_cell_lower_id_wins():
    # R1 and R2 both plan to move to (2, 0) — R1 (lower id) keeps its move
    planned = {RobotId(1): Position(2, 0), RobotId(2): Position(2, 0)}
    current = {RobotId(1): Position(1, 0), RobotId(2): Position(3, 0)}

    result = resolve_collisions(planned, current)

    assert result[RobotId(1)] == Position(2, 0)
    assert result[RobotId(2)] is None


def test_resolve_collisions_cascade_cancellation():
    # R1 at (0,0) → (1,0); R2 at (1,0) → (2,0); R3 at (2,0) stays (None)
    # Pass 1: R3 stayer at (2,0) blocks R2 mover → R2 cancelled
    # Pass 2: R2 now stayer at (1,0) blocks R1 mover → R1 cancelled
    planned = {RobotId(1): Position(1, 0), RobotId(2): Position(2, 0), RobotId(3): None}
    current = {RobotId(1): Position(0, 0), RobotId(2): Position(1, 0), RobotId(3): Position(2, 0)}

    result = resolve_collisions(planned, current)

    assert result[RobotId(1)] is None
    assert result[RobotId(2)] is None
    assert result[RobotId(3)] is None


def test_resolve_collisions_does_not_mutate_input():
    planned = {RobotId(1): Position(1, 0), RobotId(2): Position(1, 0)}
    current = {RobotId(1): Position(0, 0), RobotId(2): Position(2, 0)}
    planned_copy = dict(planned)

    resolve_collisions(planned, current)

    assert planned == planned_copy
