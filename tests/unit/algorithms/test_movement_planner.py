from simulation.domain.robot_state import RobotId
from simulation.domain.environment import Environment
from simulation.primitives.position import Position
from simulation.domain.robot_state import RobotState
from simulation.domain.task import Task, TaskId, TaskType, SpatialConstraint
from simulation.domain.task_state import TaskState, TaskStatus
from simulation.primitives.time import Time
from simulation.primitives.zone import Zone, ZoneId, ZoneType
from simulation.algorithms.movement_planner import plan_moves, resolve_collisions, resolve_task_target_position
from simulation.domain.step_context import StepContext


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


# ---------------------------------------------------------------------------
# plan_moves helpers
# ---------------------------------------------------------------------------

def _make_ctx(
    robot_id: RobotId,
    robot_pos: Position,
    task_id: TaskId = TaskId(1),
    task_type: TaskType = TaskType.ROUTINE_INSPECTION,
    task_status: TaskStatus = TaskStatus.ASSIGNED,
) -> StepContext:
    return StepContext(
        robot_states={robot_id: RobotState(robot_id=robot_id, position=robot_pos)},
        task_states={task_id: TaskState(
            task_id=task_id, status=task_status, assigned_robot_ids={robot_id}
        )},
        robot_to_task={robot_id: task_id},
        robot_by_id={},
        task_by_id={task_id: Task(
            id=task_id, type=task_type, priority=1, required_work_time=Time(1)
        )},
        environment=Environment(width=5, height=5),
        t_now=Time(0),
    )


def _stub_pathfinding(env, start, goal):
    return Position(start.x + 1, start.y)


# ---------------------------------------------------------------------------
# plan_moves
# ---------------------------------------------------------------------------

def test_plan_moves_unassigned_robot_gets_none():
    ctx = StepContext(
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        task_states={},
        robot_to_task={},
        robot_by_id={},
        task_by_id={},
        environment=Environment(width=5, height=5),
        t_now=Time(0),
    )

    result = plan_moves(ctx, pathfinding=_stub_pathfinding, goal_resolver=lambda rid, s: Position(3, 3))

    assert result[RobotId(1)] is None


def test_plan_moves_idle_task_gets_none():
    ctx = _make_ctx(RobotId(1), Position(0, 0), task_type=TaskType.IDLE)

    result = plan_moves(ctx, pathfinding=_stub_pathfinding, goal_resolver=lambda rid, s: Position(3, 3))

    assert result[RobotId(1)] is None


def test_plan_moves_done_task_gets_none():
    ctx = _make_ctx(RobotId(1), Position(0, 0), task_status=TaskStatus.DONE)

    result = plan_moves(ctx, pathfinding=_stub_pathfinding, goal_resolver=lambda rid, s: Position(3, 3))

    assert result[RobotId(1)] is None


def test_plan_moves_failed_task_gets_none():
    ctx = _make_ctx(RobotId(1), Position(0, 0), task_status=TaskStatus.FAILED)

    result = plan_moves(ctx, pathfinding=_stub_pathfinding, goal_resolver=lambda rid, s: Position(3, 3))

    assert result[RobotId(1)] is None


def test_plan_moves_no_goal_gets_none():
    ctx = _make_ctx(RobotId(1), Position(0, 0))

    result = plan_moves(ctx, pathfinding=_stub_pathfinding, goal_resolver=lambda rid, s: None)

    assert result[RobotId(1)] is None


def test_plan_moves_robot_already_at_goal_gets_none():
    pos = Position(2, 2)
    ctx = _make_ctx(RobotId(1), pos)

    result = plan_moves(ctx, pathfinding=_stub_pathfinding, goal_resolver=lambda rid, s: pos)

    assert result[RobotId(1)] is None


def test_plan_moves_returns_pathfinding_result_when_not_at_goal():
    ctx = _make_ctx(RobotId(1), Position(0, 0))
    expected_next = Position(1, 0)

    result = plan_moves(ctx, pathfinding=_stub_pathfinding, goal_resolver=lambda rid, s: Position(4, 4))

    assert result[RobotId(1)] == expected_next


def test_plan_moves_goal_resolver_receives_correct_robot_id_and_state():
    robot_id = RobotId(1)
    robot_pos = Position(2, 3)
    ctx = _make_ctx(robot_id, robot_pos)
    captured = []

    def capturing_resolver(rid, state):
        captured.append((rid, state))
        return Position(4, 4)

    plan_moves(ctx, pathfinding=_stub_pathfinding, goal_resolver=capturing_resolver)

    assert len(captured) == 1
    assert captured[0][0] == robot_id
    assert captured[0][1].position == robot_pos


def test_plan_moves_covers_all_robots():
    # Two robots, both assigned to different tasks, both should move
    r1, r2 = RobotId(1), RobotId(2)
    t1, t2 = TaskId(1), TaskId(2)
    ctx = StepContext(
        robot_states={
            r1: RobotState(robot_id=r1, position=Position(0, 0)),
            r2: RobotState(robot_id=r2, position=Position(1, 0)),
        },
        task_states={
            t1: TaskState(task_id=t1, status=TaskStatus.ASSIGNED, assigned_robot_ids={r1}),
            t2: TaskState(task_id=t2, status=TaskStatus.ASSIGNED, assigned_robot_ids={r2}),
        },
        robot_to_task={r1: t1, r2: t2},
        robot_by_id={},
        task_by_id={
            t1: Task(id=t1, type=TaskType.ROUTINE_INSPECTION, priority=1, required_work_time=Time(1)),
            t2: Task(id=t2, type=TaskType.ROUTINE_INSPECTION, priority=1, required_work_time=Time(1)),
        },
        environment=Environment(width=5, height=5),
        t_now=Time(0),
    )

    result = plan_moves(ctx, pathfinding=_stub_pathfinding, goal_resolver=lambda rid, s: Position(4, 4))

    assert set(result.keys()) == {r1, r2}
