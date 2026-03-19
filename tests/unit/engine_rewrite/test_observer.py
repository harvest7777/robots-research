"""
Unit tests for classify_step (Observer).

Each test exercises one business rule in isolation.
No file I/O, no services, no MCP.
"""

from __future__ import annotations

import pytest

from simulation.algorithms import astar_pathfind
from simulation.domain import (
    TaskId, Environment, RescuePoint, Robot, RobotId, RobotState,
    SearchTask, SearchTaskState, WorkTask, SpatialConstraint, TaskState,
)
from simulation.primitives import Capability, Position, Time, Zone, ZoneId, ZoneType
from simulation.engine_rewrite import Assignment, SimulationState, IgnoreReason
from simulation.engine_rewrite._observer import classify_step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(width: int = 20, height: int = 20) -> Environment:
    return Environment(width=width, height=height)


def _robot(rid: int, capabilities: frozenset = frozenset()) -> Robot:
    return Robot(id=RobotId(rid), capabilities=capabilities)


def _robot_state(rid: int, x: int, y: int, battery: float = 1.0) -> RobotState:
    return RobotState(robot_id=RobotId(rid), position=Position(x, y), battery_level=battery)


def _work_task(tid: int, x: int, y: int, work: int = 10, caps: frozenset = frozenset(), max_distance=0) -> WorkTask:
    return WorkTask(
        id=TaskId(tid),
        priority=5,
        required_work_time=Time(work),
        spatial_constraint=SpatialConstraint(target=Position(x, y), max_distance=max_distance),
        required_capabilities=caps,
    )


def _task_state(tid: int, work_done: int = 0) -> TaskState:
    return TaskState(task_id=TaskId(tid), work_done=Time(work_done))


def _state(
    robots: list[Robot],
    robot_states: list[RobotState],
    tasks: list,
    task_states: list,
    env: Environment | None = None,
    assignments: list[Assignment] | None = None,
) -> SimulationState:
    return SimulationState(
        environment=env or _env(),
        robots={r.id: r for r in robots},
        robot_states={rs.robot_id: rs for rs in robot_states},
        tasks={t.id: t for t in tasks},
        task_states={ts.task_id: ts for ts in task_states},
        assignments=tuple(assignments or []),
    )


def _assign(robot_id: int, task_id: int) -> Assignment:
    return Assignment(task_id=TaskId(task_id), robot_id=RobotId(robot_id))


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------

def test_robot_moves_toward_task():
    task = _work_task(1, x=5, y=0)
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=0, y=0)],
        tasks=[task],
        task_states=[_task_state(1)],
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert len(outcome.moved) == 1
    rid, pos = outcome.moved[0]
    assert rid == RobotId(1)
    assert pos != Position(0, 0)


def test_robot_at_goal_does_not_move():
    task = _work_task(1, x=3, y=3)
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=3, y=3)],
        tasks=[task],
        task_states=[_task_state(1)],
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.moved == []
    assert (RobotId(1), TaskId(1)) in outcome.worked


def test_collision_resolution_only_one_robot_moves_to_contested_cell():
    task1 = _work_task(1, x=5, y=0)
    task2 = _work_task(2, x=5, y=0)
    state = _state(
        robots=[_robot(1), _robot(2)],
        robot_states=[_robot_state(1, x=4, y=0), _robot_state(2, x=6, y=0)],
        tasks=[task1, task2],
        task_states=[_task_state(1), _task_state(2)],
        assignments=[_assign(1, 1), _assign(2, 2)],
    )
    outcome = classify_step(state, astar_pathfind)
    destinations = [pos for _, pos in outcome.moved]
    assert len(destinations) == len(set(destinations)), "two robots ended on same cell"


def test_head_on_swap_robots_pass_through_each_other():
    # Robot 1 at (2, 0) heading right toward task at (9, 0).
    # Robot 2 at (3, 0) heading left toward task at (0, 0).
    # Both want to step into each other's current cell — resolve_collisions
    # sees no shared *destination* so both moves succeed: they swap positions
    # in one tick, effectively teleporting through each other.
    task1 = _work_task(1, x=9, y=0)
    task2 = _work_task(2, x=0, y=0)
    state = _state(
        robots=[_robot(1), _robot(2)],
        robot_states=[_robot_state(1, x=2, y=0), _robot_state(2, x=3, y=0)],
        tasks=[task1, task2],
        task_states=[_task_state(1), _task_state(2)],
        assignments=[_assign(1, 1), _assign(2, 2)],
    )
    outcome = classify_step(state, astar_pathfind)

    moved = dict(outcome.moved)
    # Both robots move — the swap is not blocked
    assert RobotId(1) in moved
    assert RobotId(2) in moved
    # They land on each other's former positions
    assert moved[RobotId(1)] == Position(3, 0)
    assert moved[RobotId(2)] == Position(2, 0)


# ---------------------------------------------------------------------------
# Work
# ---------------------------------------------------------------------------

def test_robot_satisfying_work_conditions_works():
    task = _work_task(1, x=2, y=2)
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=2, y=2)],
        tasks=[task],
        task_states=[_task_state(1)],
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert (RobotId(1), TaskId(1)) in outcome.worked


def test_robot_not_satisfying_task_spatial_constraint_does_not_work():
    task = _work_task(1, x=10, y=10)
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=0, y=0)],
        tasks=[task],
        task_states=[_task_state(1)],
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.worked == []


def test_task_completes_when_work_reaches_required():
    task = _work_task(1, x=0, y=0, work=3)
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=0, y=0)],
        tasks=[task],
        task_states=[_task_state(1, work_done=2)],  # 1 tick away from done
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert TaskId(1) in outcome.tasks_completed


def test_task_not_complete_when_work_below_required():
    task = _work_task(1, x=0, y=0, work=5)
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=0, y=0)],
        tasks=[task],
        task_states=[_task_state(1, work_done=2)],
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert TaskId(1) not in outcome.tasks_completed


def test_multiple_robots_contribute_work_this_tick():
    task = _work_task(1, x=0, y=0, work=10, max_distance=1)
    state = _state(
        robots=[_robot(1), _robot(2)],
        robot_states=[_robot_state(1, x=0, y=1), _robot_state(2, x=0, y=0)],
        tasks=[task],
        task_states=[_task_state(1, work_done=8)],  # needs 2 more; 2 robots = done
        assignments=[_assign(1, 1), _assign(2, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert TaskId(1) in outcome.tasks_completed


# ---------------------------------------------------------------------------
# IgnoreReason — business rules
# ---------------------------------------------------------------------------

def test_dead_battery_is_ignored():
    task = _work_task(1, x=0, y=0)
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=0, y=0, battery=0.0)],
        tasks=[task],
        task_states=[_task_state(1)],
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    reasons = [r for _, r in outcome.assignments_ignored]
    assert IgnoreReason.NO_BATTERY in reasons


def test_wrong_capability_is_ignored():
    caps = frozenset([Capability.VISION])
    task = _work_task(1, x=0, y=0, caps=caps)
    state = _state(
        robots=[_robot(1, capabilities=frozenset())],
        robot_states=[_robot_state(1, x=0, y=0)],
        tasks=[task],
        task_states=[_task_state(1)],
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    reasons = [r for _, r in outcome.assignments_ignored]
    assert IgnoreReason.WRONG_CAPABILITY in reasons


def test_terminal_task_is_ignored():
    from simulation.domain import TaskStatus
    task = _work_task(1, x=0, y=0)
    ts = TaskState(task_id=TaskId(1), status=TaskStatus.DONE)
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=0, y=0)],
        tasks=[task],
        task_states=[ts],
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    reasons = [r for _, r in outcome.assignments_ignored]
    assert IgnoreReason.TASK_TERMINAL in reasons


def test_no_path_is_ignored():
    env = Environment(width=5, height=5)
    for y in range(5):
        env.add_obstacle(Position(1, y))
    task = _work_task(1, x=4, y=0)
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=0, y=0)],
        tasks=[task],
        task_states=[_task_state(1)],
        env=env,
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    reasons = [r for _, r in outcome.assignments_ignored]
    assert IgnoreReason.NO_PATH in reasons


# ---------------------------------------------------------------------------
# Waypoints
# ---------------------------------------------------------------------------

def test_waypoint_set_to_position_target():
    # Task has an exact Position target — waypoint should be that position.
    task = _work_task(1, x=7, y=3)
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=0, y=0)],
        tasks=[task],
        task_states=[_task_state(1)],
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.waypoints[RobotId(1)] == Position(7, 3)


def test_waypoint_set_to_nearest_zone_cell():
    # Task targets a zone — waypoint should be the zone cell nearest the robot.
    env = _env()
    zone = Zone.from_positions(ZoneId(1), ZoneType.INSPECTION, [Position(8, 0), Position(8, 5)])
    env.add_zone(zone)
    task = WorkTask(
        id=TaskId(1),
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=ZoneId(1)),
    )
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=0, y=0)],  # closer to (8,0) than (8,5)
        tasks=[task],
        task_states=[_task_state(1)],
        env=env,
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.waypoints[RobotId(1)] == Position(8, 0)


def test_waypoint_nearest_zone_cell_tracks_robot_position():
    # Same zone, robot on the opposite side — nearest cell should flip.
    env = _env()
    zone = Zone.from_positions(ZoneId(1), ZoneType.INSPECTION, [Position(8, 0), Position(8, 5)])
    env.add_zone(zone)
    task = WorkTask(
        id=TaskId(1),
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=ZoneId(1)),
    )
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=0, y=5)],  # closer to (8,5) than (8,0)
        tasks=[task],
        task_states=[_task_state(1)],
        env=env,
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.waypoints[RobotId(1)] == Position(8, 5)


def test_waypoint_not_set_when_task_has_no_spatial_constraint():
    # A task with no spatial_constraint has no meaningful goal — no waypoint.
    task = WorkTask(
        id=TaskId(1),
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=None,
    )
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=0, y=0)],
        tasks=[task],
        task_states=[_task_state(1)],
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert RobotId(1) not in outcome.waypoints


def test_waypoint_set_even_when_robot_already_at_goal():
    # Robot is already at the task position — it works in place but the waypoint
    # is still recorded (it's the goal, not the intended move).
    task = _work_task(1, x=4, y=4)
    state = _state(
        robots=[_robot(1)],
        robot_states=[_robot_state(1, x=4, y=4)],
        tasks=[task],
        task_states=[_task_state(1)],
        assignments=[_assign(1, 1)],
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.waypoints[RobotId(1)] == Position(4, 4)
    assert outcome.moved == []


# ---------------------------------------------------------------------------
# Search and rescue
# ---------------------------------------------------------------------------

def test_search_robot_discovers_rescue_point_when_at_position():
    _rp_task = WorkTask(
        id=TaskId(1),
        priority=10,
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
        required_work_time=Time(20),
        min_robots_needed=1,
    )
    rescue_point = RescuePoint(
        id=TaskId(1),
        name="Alpha",
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
        task=_rp_task,
        initial_task_state=TaskState(task_id=TaskId(1)),
    )
    env = _env()
    env.add_rescue_point(rescue_point)

    search_task = SearchTask(id=TaskId(1), priority=5)
    search_state = SearchTaskState(
        task_id=TaskId(1),
        rescue_found=frozenset(),
    )
    state = SimulationState(
        environment=env,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _robot_state(1, x=5, y=5)},
        tasks={TaskId(1): search_task},
        task_states={TaskId(1): search_state},
        assignments=(_assign(1, 1),),
    )
    outcome = classify_step(state, astar_pathfind)
    assert TaskId(1) in outcome.rescue_points_found
    assert len(outcome.tasks_spawned) == 1
    assert TaskId(1) in outcome.tasks_completed


def test_already_found_rescue_point_not_re_discovered():
    _rp_task = WorkTask(
        id=TaskId(1),
        priority=10,
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
        required_work_time=Time(20),
        min_robots_needed=1,
    )
    rescue_point = RescuePoint(
        id=TaskId(1),
        name="Alpha",
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
        task=_rp_task,
        initial_task_state=TaskState(task_id=TaskId(1)),
    )
    env = _env()
    env.add_rescue_point(rescue_point)

    search_task = SearchTask(id=TaskId(1), priority=5)
    search_state = SearchTaskState(
        task_id=TaskId(1),
        rescue_found=frozenset({TaskId(1)}),  # already found
    )
    state = SimulationState(
        environment=env,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _robot_state(1, x=5, y=5)},
        tasks={TaskId(1): search_task},
        task_states={TaskId(1): search_state},
        assignments=(_assign(1, 1),),
    )
    outcome = classify_step(state, astar_pathfind)
    assert outcome.rescue_points_found == []
    assert outcome.tasks_spawned == []


def test_spawned_rescue_task_has_correct_location_and_work_time():
    _rp_task = WorkTask(
        id=TaskId(1),
        priority=10,
        spatial_constraint=SpatialConstraint(target=Position(3, 3), max_distance=0),
        required_work_time=Time(30),
        min_robots_needed=2,
    )
    rescue_point = RescuePoint(
        id=TaskId(1),
        name="Bravo",
        spatial_constraint=SpatialConstraint(target=Position(3, 3), max_distance=0),
        task=_rp_task,
        initial_task_state=TaskState(task_id=TaskId(1)),
    )
    env = _env()
    env.add_rescue_point(rescue_point)

    search_task = SearchTask(id=TaskId(1), priority=5)
    search_state = SearchTaskState(
        task_id=TaskId(1),
        rescue_found=frozenset(),
    )
    state = SimulationState(
        environment=env,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _robot_state(1, x=3, y=3)},
        tasks={TaskId(1): search_task},
        task_states={TaskId(1): search_state},
        assignments=(_assign(1, 1),),
    )
    outcome = classify_step(state, astar_pathfind)
    assert len(outcome.tasks_spawned) == 1
    spawned, _ = outcome.tasks_spawned[0]
    assert isinstance(spawned, WorkTask)
    assert spawned.required_work_time == Time(30)
    assert spawned.min_robots_needed == 2
    assert spawned.spatial_constraint is not None
    assert spawned.spatial_constraint.target == Position(3, 3)


def test_search_task_not_complete_when_rescue_point_remaining():
    _rp_task_found = WorkTask(
        id=TaskId(2),
        priority=10,
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
        required_work_time=Time(10),
    )
    rp_found = RescuePoint(
        id=TaskId(2),
        name="Alpha",
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
        task=_rp_task_found,
        initial_task_state=TaskState(task_id=TaskId(2)),
    )
    _rp_task_unfound = WorkTask(
        id=TaskId(3),
        priority=10,
        spatial_constraint=SpatialConstraint(target=Position(9, 9), max_distance=0),
        required_work_time=Time(10),
    )
    rp_unfound = RescuePoint(
        id=TaskId(3),
        name="Bravo",
        spatial_constraint=SpatialConstraint(target=Position(9, 9), max_distance=0),
        task=_rp_task_unfound,
        initial_task_state=TaskState(task_id=TaskId(3)),
    )
    env = _env()
    env.add_rescue_point(rp_found)
    env.add_rescue_point(rp_unfound)

    search_task = SearchTask(id=TaskId(1), priority=5)
    search_state = SearchTaskState(task_id=TaskId(1), rescue_found=frozenset())
    state = SimulationState(
        environment=env,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _robot_state(1, x=5, y=5)},
        tasks={TaskId(1): search_task},
        task_states={TaskId(1): search_state},
        assignments=(_assign(1, 1),),
    )
    outcome = classify_step(state, astar_pathfind)
    # Finds rp_found this tick but rp_unfound is still missing
    assert TaskId(2) in outcome.rescue_points_found
    assert TaskId(1) not in outcome.tasks_completed


def test_search_task_completes_when_last_rescue_point_found():
    # Simulates a multi-tick scenario: one rescue point was already found in a
    # previous tick (reflected in rescue_found), robot discovers the last one
    # this tick — search task should complete.
    _rp_task_previous = WorkTask(
        id=TaskId(2),
        priority=10,
        spatial_constraint=SpatialConstraint(target=Position(1, 1), max_distance=0),
        required_work_time=Time(10),
    )
    rp_previous = RescuePoint(
        id=TaskId(2),
        name="Alpha",
        spatial_constraint=SpatialConstraint(target=Position(1, 1), max_distance=0),
        task=_rp_task_previous,
        initial_task_state=TaskState(task_id=TaskId(2)),
    )
    _rp_task_last = WorkTask(
        id=TaskId(3),
        priority=10,
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
        required_work_time=Time(10),
    )
    rp_last = RescuePoint(
        id=TaskId(3),
        name="Bravo",
        spatial_constraint=SpatialConstraint(target=Position(5, 5), max_distance=0),
        task=_rp_task_last,
        initial_task_state=TaskState(task_id=TaskId(3)),
    )
    env = _env()
    env.add_rescue_point(rp_previous)
    env.add_rescue_point(rp_last)

    search_task = SearchTask(id=TaskId(1), priority=5)
    search_state = SearchTaskState(
        task_id=TaskId(1),
        rescue_found=frozenset({TaskId(2)}),  # rp_previous already found last tick
    )
    state = SimulationState(
        environment=env,
        robots={RobotId(1): _robot(1)},
        robot_states={RobotId(1): _robot_state(1, x=5, y=5)},  # at rp_last
        tasks={TaskId(1): search_task},
        task_states={TaskId(1): search_state},
        assignments=(_assign(1, 1),),
    )
    outcome = classify_step(state, astar_pathfind)
    assert TaskId(3) in outcome.rescue_points_found
    assert TaskId(1) in outcome.tasks_completed
