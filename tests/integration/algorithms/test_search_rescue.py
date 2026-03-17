"""
Integration tests for search-and-rescue behaviour (OLD ENGINE).

These tests cover the old Simulation engine's search-and-rescue path.
They are skipped pending Phase 6 cleanup: RescuePoint now inherits from
WorkTask and its id IS the task id, which breaks the old pre-seeding model
where rescue_task_id was a separate field pointing to a different Task.

The equivalent behaviour is covered by the new engine unit tests in
tests/unit/engine_rewrite/.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Old engine search-rescue tests — superseded by engine_rewrite. "
           "RescuePoint now inherits WorkTask; pre-seeded rescue task model removed. "
           "Will be deleted in Phase 6."
)

from simulation.algorithms.astar_pathfinding import astar_pathfind
from scenario_loaders.load_simulation import load_simulation
from services.in_memory_assignment_service import InMemoryAssignmentService
from simulation.domain.assignment import Assignment
from simulation.domain.robot_state import RobotId
from simulation.domain.environment import Environment
from simulation.primitives.position import Position
from simulation.domain.rescue_point import RescuePoint, RescuePointId
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotState
from simulation.algorithms.search_goal import compute_search_goal
from simulation.engine.simulation import Simulation
from simulation.domain.base_task import TaskId, TaskStatus
from simulation.domain.task import Task, TaskType, SpatialConstraint
from simulation.domain.task_state import TaskState
from simulation.domain.search_task import SearchTask, SearchTaskState
from simulation.primitives.time import Time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_search_sim(
    *,
    robot_pos: Position = Position(0, 0),
    rescue_pos: Position | None = None,
    env_size: int = 20,
    proximity_threshold: int = 10,
    min_robots_needed: int = 1,
) -> Simulation:
    """Minimal simulation with one SearchTask robot and an optional rescue point."""
    env = Environment(env_size, env_size)
    robot_id = RobotId(1)
    robot = Robot(id=robot_id, capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=robot_id, position=robot_pos)

    search_task_id = TaskId(10)
    search_task = SearchTask(
        id=search_task_id,
        priority=5,
        proximity_threshold=proximity_threshold,
    )
    search_task_state = SearchTaskState(task_id=search_task_id)

    rescue_task_id = TaskId(20)
    rescue_task = Task(
        id=rescue_task_id,
        type=TaskType.RESCUE,
        priority=10,
        required_work_time=Time(5),
        min_robots_needed=min_robots_needed,
        spatial_constraint=SpatialConstraint(
            target=rescue_pos if rescue_pos is not None else Position(5, 5)
        ),
    )
    rescue_task_state = TaskState(task_id=rescue_task_id)

    if rescue_pos is not None:
        rp = RescuePoint(
            id=RescuePointId(1),
            position=rescue_pos,
            name="Test Point",
            rescue_task_id=rescue_task_id,
        )
        env.add_rescue_point(rp)
        search_task_state.rescue_found[RescuePointId(1)] = False

    assignment_service = InMemoryAssignmentService([
        Assignment(task_id=search_task_id, robot_ids=frozenset([robot_id]), assign_at=Time(0))
    ])

    sim = Simulation(
        environment=env,
        robots=[robot, Robot(id=RobotId(99), capabilities=frozenset(), speed=1)],
        tasks=[search_task, rescue_task],
        robot_states={
            robot_id: robot_state,
            RobotId(99): RobotState(robot_id=RobotId(99), position=Position(9, 9)),
        },
        task_states={search_task_id: search_task_state, rescue_task_id: rescue_task_state},
        assignment_service=assignment_service,
        pathfinding_algorithm=astar_pathfind,
    )
    return sim


def _search_state(sim: Simulation, task_id: int = 10) -> SearchTaskState:
    state = sim.task_states[TaskId(task_id)]
    assert isinstance(state, SearchTaskState)
    return state


# ---------------------------------------------------------------------------
# 1. Search robot picks random waypoint when none set
# ---------------------------------------------------------------------------

def test_search_robot_picks_waypoint_when_none_set():
    sim = _make_search_sim()
    state = sim.robot_states[RobotId(1)]
    assert state.current_waypoint is None

    sim._step()

    assert state.current_waypoint is not None
    assert sim.environment.in_bounds(state.current_waypoint)
    assert state.current_waypoint not in sim.environment.obstacles


# ---------------------------------------------------------------------------
# 2. Search robot locks onto rescue point within proximity threshold
# ---------------------------------------------------------------------------

def test_search_robot_locks_onto_rescue_point_within_threshold():
    rescue_pos = Position(10, 0)  # Manhattan distance 10 from (0,0) == threshold
    sim = _make_search_sim(robot_pos=Position(0, 0), rescue_pos=rescue_pos)
    state = sim.robot_states[RobotId(1)]
    search_state = _search_state(sim)

    goal = compute_search_goal(
        state,
        sim.environment.rescue_points,
        search_state.rescue_found,
        sim.tasks[0].proximity_threshold,  # type: ignore[union-attr]
        sim.pathfinding_algorithm,
        sim.environment,
    )

    assert goal == rescue_pos


# ---------------------------------------------------------------------------
# 3. Search robot does NOT lock beyond proximity threshold
# ---------------------------------------------------------------------------

def test_search_robot_does_not_lock_beyond_threshold():
    rescue_pos = Position(11, 0)  # Manhattan distance 11 > threshold 10
    sim = _make_search_sim(robot_pos=Position(0, 0), rescue_pos=rescue_pos)
    state = sim.robot_states[RobotId(1)]
    search_state = _search_state(sim)

    goal = compute_search_goal(
        state,
        sim.environment.rescue_points,
        search_state.rescue_found,
        sim.tasks[0].proximity_threshold,  # type: ignore[union-attr]
        sim.pathfinding_algorithm,
        sim.environment,
    )

    assert goal != rescue_pos


# ---------------------------------------------------------------------------
# 4. Search robot immediately locks if it starts within threshold
# ---------------------------------------------------------------------------

def test_search_robot_locks_immediately_if_starts_within_threshold():
    rescue_pos = Position(3, 3)
    robot_pos = Position(3, 13)  # Manhattan = 10, exactly at threshold
    sim = _make_search_sim(robot_pos=robot_pos, rescue_pos=rescue_pos)
    state = sim.robot_states[RobotId(1)]
    search_state = _search_state(sim)

    goal = compute_search_goal(
        state,
        sim.environment.rescue_points,
        search_state.rescue_found,
        sim.tasks[0].proximity_threshold,  # type: ignore[union-attr]
        sim.pathfinding_algorithm,
        sim.environment,
    )
    assert goal == rescue_pos


# ---------------------------------------------------------------------------
# 5. rescue_found becomes True when robot arrives at rescue point position
# ---------------------------------------------------------------------------

def test_rescue_found_set_when_robot_arrives():
    rescue_pos = Position(1, 0)
    sim = _make_search_sim(robot_pos=rescue_pos, rescue_pos=rescue_pos)
    rp_id = RescuePointId(1)

    assert _search_state(sim).rescue_found[rp_id] is False

    sim._step()

    assert _search_state(sim).rescue_found[rp_id] is True


# ---------------------------------------------------------------------------
# 6. Search task marked DONE when rescue found (single rescue point)
# ---------------------------------------------------------------------------

def test_search_task_marked_done_when_all_rescues_found():
    rescue_pos = Position(1, 0)
    sim = _make_search_sim(robot_pos=rescue_pos, rescue_pos=rescue_pos)

    sim._step()

    assert sim.task_states[TaskId(10)].status == TaskStatus.DONE


# ---------------------------------------------------------------------------
# 7. No rescue points → simulation runs to budget (SearchTask never finishes)
# ---------------------------------------------------------------------------

def test_no_rescue_points_simulation_runs_to_budget():
    env = Environment(5, 5)
    robot_id = RobotId(1)
    robot = Robot(id=robot_id, capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=robot_id, position=Position(0, 0))

    search_task_id = TaskId(10)
    search_task = SearchTask(id=search_task_id, priority=5, proximity_threshold=10)
    search_task_state = SearchTaskState(task_id=search_task_id)

    assignment_service = InMemoryAssignmentService([
        Assignment(task_id=search_task_id, robot_ids=frozenset([robot_id]), assign_at=Time(0))
    ])

    sim = Simulation(
        environment=env,
        robots=[robot],
        tasks=[search_task],
        robot_states={robot_id: robot_state},
        task_states={search_task_id: search_task_state},
        assignment_service=assignment_service,
        pathfinding_algorithm=astar_pathfind,
    )

    result = sim.run(max_delta_time=Time(10))
    assert not result.completed
    assert result.makespan is None


# ---------------------------------------------------------------------------
# 8. Multiple robots at same rescue point → deterministic (lowest robot_id)
# ---------------------------------------------------------------------------

def test_multiple_robots_at_rescue_point_deterministic():
    rescue_pos = Position(5, 5)
    env = Environment(10, 10)
    rp = RescuePoint(id=RescuePointId(1), position=rescue_pos, name="Alpha", rescue_task_id=TaskId(20))
    env.add_rescue_point(rp)

    r1_id = RobotId(1)
    r2_id = RobotId(2)
    search_task_id = TaskId(10)
    rescue_task_id = TaskId(20)

    search_task = SearchTask(id=search_task_id, priority=5, proximity_threshold=10)
    search_task_state = SearchTaskState(
        task_id=search_task_id,
        rescue_found={RescuePointId(1): False},
    )
    rescue_task = Task(
        id=rescue_task_id,
        type=TaskType.RESCUE,
        priority=10,
        required_work_time=Time(5),
        min_robots_needed=1,
        spatial_constraint=SpatialConstraint(target=rescue_pos),
    )

    assignment_service = InMemoryAssignmentService([
        Assignment(task_id=search_task_id, robot_ids=frozenset([r1_id, r2_id]), assign_at=Time(0))
    ])

    sim = Simulation(
        environment=env,
        robots=[
            Robot(id=r1_id, capabilities=frozenset(), speed=1),
            Robot(id=r2_id, capabilities=frozenset(), speed=1),
        ],
        tasks=[search_task, rescue_task],
        robot_states={
            r1_id: RobotState(robot_id=r1_id, position=rescue_pos),
            r2_id: RobotState(robot_id=r2_id, position=rescue_pos),
        },
        task_states={
            search_task_id: search_task_state,
            rescue_task_id: TaskState(task_id=rescue_task_id),
        },
        assignment_service=assignment_service,
        pathfinding_algorithm=astar_pathfind,
    )

    sim._step()

    assert _search_state(sim).rescue_found[RescuePointId(1)] is True
    assert sim.task_states[search_task_id].status == TaskStatus.DONE


# ---------------------------------------------------------------------------
# 9. add_rescue_point at obstacle position raises ValueError
# ---------------------------------------------------------------------------

def test_add_rescue_point_on_obstacle_raises():
    env = Environment(5, 5)
    obstacle_pos = Position(2, 2)
    env.add_obstacle(obstacle_pos)

    rp = RescuePoint(id=RescuePointId(1), position=obstacle_pos, name="Bad", rescue_task_id=TaskId(1))

    with pytest.raises(ValueError, match="obstacle"):
        env.add_rescue_point(rp)


# ---------------------------------------------------------------------------
# 10. snapshot task_states carries SearchTaskState with rescue_found
# ---------------------------------------------------------------------------

def test_snapshot_search_task_state_carries_rescue_found():
    rescue_pos = Position(1, 0)
    sim = _make_search_sim(robot_pos=rescue_pos, rescue_pos=rescue_pos)
    rp_id = RescuePointId(1)

    snap_before = sim.snapshot()
    search_snap_before = snap_before.task_states[TaskId(10)]
    assert isinstance(search_snap_before, SearchTaskState)
    assert search_snap_before.rescue_found[rp_id] is False

    sim._step()

    snap_after = sim.snapshot()
    search_snap_after = snap_after.task_states[TaskId(10)]
    assert isinstance(search_snap_after, SearchTaskState)
    assert search_snap_after.rescue_found[rp_id] is True


# ---------------------------------------------------------------------------
# 11. min_robots_needed: only that many robots allocated on discovery
# ---------------------------------------------------------------------------

def test_min_robots_needed_limits_allocation_from_search_pool():
    rescue_pos = Position(0, 0)
    env = Environment(10, 10)
    rp = RescuePoint(id=RescuePointId(1), position=rescue_pos, name="Alpha", rescue_task_id=TaskId(20))
    env.add_rescue_point(rp)

    search_task_id = TaskId(10)
    rescue_task_id = TaskId(20)
    r_ids = [RobotId(i) for i in range(1, 5)]  # 4 search robots

    search_task = SearchTask(id=search_task_id, priority=5, proximity_threshold=10)
    search_task_state = SearchTaskState(
        task_id=search_task_id,
        rescue_found={RescuePointId(1): False},
    )
    rescue_task = Task(
        id=rescue_task_id,
        type=TaskType.RESCUE,
        priority=10,
        required_work_time=Time(5),
        min_robots_needed=2,  # only 2 of the 4 should be pulled
        spatial_constraint=SpatialConstraint(target=rescue_pos),
    )

    assignment_service = InMemoryAssignmentService([
        Assignment(task_id=search_task_id, robot_ids=frozenset(r_ids), assign_at=Time(0))
    ])

    sim = Simulation(
        environment=env,
        robots=[Robot(id=rid, capabilities=frozenset(), speed=1) for rid in r_ids],
        tasks=[search_task, rescue_task],
        robot_states={rid: RobotState(robot_id=rid, position=rescue_pos) for rid in r_ids},
        task_states={
            search_task_id: search_task_state,
            rescue_task_id: TaskState(task_id=rescue_task_id),
        },
        assignment_service=assignment_service,
        pathfinding_algorithm=astar_pathfind,
    )

    sim._step()

    assignments = assignment_service.get_assignments_for_time(sim.t_now)
    rescue_assignments = [a for a in assignments if a.task_id == rescue_task_id]
    assert len(rescue_assignments) == 1
    assert len(rescue_assignments[0].robot_ids) == 2


# ---------------------------------------------------------------------------
# 12. Load search_rescue.json → SearchTask loaded correctly
# ---------------------------------------------------------------------------

def test_load_search_rescue_scenario():
    sim = load_simulation("scenarios/search_rescue.json")

    rescue_points = sim.environment.rescue_points
    assert len(rescue_points) == 1

    rp = list(rescue_points.values())[0]
    assert rp.id == RescuePointId(1)
    assert rp.name == "Survivor Alpha"
    assert rp.position == Position(33, 33)
    assert rp.rescue_task_id == TaskId(20)

    search_tasks = [t for t in sim.tasks if isinstance(t, SearchTask)]
    assert len(search_tasks) == 1
    assert search_tasks[0].id == TaskId(10)
    assert search_tasks[0].proximity_threshold == 10

    search_state = sim.task_states[TaskId(10)]
    assert isinstance(search_state, SearchTaskState)
    assert RescuePointId(1) in search_state.rescue_found
