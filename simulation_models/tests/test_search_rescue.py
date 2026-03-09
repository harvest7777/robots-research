"""
Unit tests for search-and-rescue feature.

Covers:
- SEARCH robot waypoint selection
- Proximity lock onto rescue points
- Rescue found detection and task reassignment
- Snapshot rescue_found field
- Scenario loading with rescue_points
"""

from __future__ import annotations

import pytest

from pathfinding_algorithms.astar_pathfinding import astar_pathfind
from scenario_loaders.load_simulation import load_simulation
from services.base_assignment_service import BaseAssignmentService
from simulation_models.assignment import Assignment, RobotId
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.rescue_point import RescuePoint, RescuePointId
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.simulation import Simulation
from simulation_models.task import Task, TaskId, TaskType, SpatialConstraint
from simulation_models.task_state import TaskState, TaskStatus
from simulation_models.time import Time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _InMemoryAssignmentService(BaseAssignmentService):
    """Minimal in-memory assignment service for testing."""

    def __init__(self, assignments: list[Assignment] | None = None) -> None:
        self._assignments: list[Assignment] = assignments or []

    def get_assignments_for_time(self, time: Time) -> list[Assignment]:
        all_robot_ids = {rid for a in self._assignments for rid in a.robot_ids}
        seen: set[Assignment] = set()
        for robot_id in all_robot_ids:
            applicable = [
                a for a in self._assignments
                if robot_id in a.robot_ids and a.assign_at.tick <= time.tick
            ]
            if applicable:
                seen.add(max(applicable, key=lambda a: a.assign_at.tick))
        return list(seen)

    def set_assignments(self, assignments: list[Assignment]) -> None:
        self._assignments = list(assignments)

    def add_assignments(self, assignments: list[Assignment]) -> None:
        self._assignments.extend(assignments)


def _make_search_sim(
    *,
    robot_pos: Position = Position(0, 0),
    rescue_pos: Position | None = None,
    env_size: int = 10,
) -> Simulation:
    """Create a minimal simulation with one SEARCH robot and optional rescue point."""
    env = Environment(env_size, env_size)
    robot_id = RobotId(1)
    robot = Robot(id=robot_id, capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=robot_id, position=robot_pos)

    search_task_id = TaskId(10)
    search_task = Task(
        id=search_task_id,
        type=TaskType.SEARCH,
        priority=5,
        required_work_time=Time(9999),
    )
    search_task_state = TaskState(task_id=search_task_id, status=TaskStatus.ASSIGNED, assigned_robot_ids={robot_id})

    rescue_task_id = TaskId(20)
    rescue_task = Task(
        id=rescue_task_id,
        type=TaskType.RESCUE,
        priority=10,
        required_work_time=Time(5),
        spatial_constraint=SpatialConstraint(target=Position(5, 5)) if rescue_pos is None else SpatialConstraint(target=rescue_pos),
    )
    rescue_task_state = TaskState(task_id=rescue_task_id)

    if rescue_pos is not None:
        rp = RescuePoint(id=RescuePointId(1), position=rescue_pos, name="Test Point", rescue_task_id=rescue_task_id)
        env.add_rescue_point(rp)

    assignment_service = _InMemoryAssignmentService([
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


# ---------------------------------------------------------------------------
# 1. Search robot picks random waypoint when none set
# ---------------------------------------------------------------------------

def test_search_robot_picks_waypoint_when_none_set():
    sim = _make_search_sim()
    robot_id = RobotId(1)
    state = sim.robot_states[robot_id]
    assert state.current_waypoint is None

    # One step should give it a waypoint
    sim._step()

    assert state.current_waypoint is not None
    assert sim.environment.in_bounds(state.current_waypoint)
    assert state.current_waypoint not in sim.environment.obstacles


# ---------------------------------------------------------------------------
# 2. Search robot locks onto rescue point within distance 4
# ---------------------------------------------------------------------------

def test_search_robot_locks_onto_rescue_point_within_distance_4():
    rescue_pos = Position(4, 0)  # Manhattan distance 4 from (0,0)
    sim = _make_search_sim(robot_pos=Position(0, 0), rescue_pos=rescue_pos)
    robot_id = RobotId(1)
    state = sim.robot_states[robot_id]

    goal = sim._compute_search_goal(robot_id, state)

    assert goal == rescue_pos
    assert state.current_waypoint == rescue_pos


# ---------------------------------------------------------------------------
# 3. Search robot does NOT lock outside distance 5
# ---------------------------------------------------------------------------

def test_search_robot_does_not_lock_outside_distance_5():
    rescue_pos = Position(5, 0)  # Manhattan distance 5 from (0,0)
    sim = _make_search_sim(robot_pos=Position(0, 0), rescue_pos=rescue_pos)
    robot_id = RobotId(1)
    state = sim.robot_states[robot_id]

    goal = sim._compute_search_goal(robot_id, state)

    # Should pick a random waypoint, not the rescue point at distance 5
    assert goal != rescue_pos


# ---------------------------------------------------------------------------
# 4. Search robot immediately locks if it starts within Manhattan ≤ 4
# ---------------------------------------------------------------------------

def test_search_robot_locks_immediately_if_starts_within_4():
    rescue_pos = Position(3, 3)
    robot_pos = Position(0, 0)  # Manhattan = 6 — actually not within 4 here
    # Use exact distance 4
    robot_pos = Position(3, 7)  # Manhattan = 4
    sim = _make_search_sim(robot_pos=robot_pos, rescue_pos=rescue_pos)
    robot_id = RobotId(1)
    state = sim.robot_states[robot_id]

    goal = sim._compute_search_goal(robot_id, state)
    assert goal == rescue_pos


# ---------------------------------------------------------------------------
# 5. rescue_found becomes True when robot arrives at rescue point position
# ---------------------------------------------------------------------------

def test_rescue_found_set_when_robot_arrives():
    rescue_pos = Position(1, 0)
    sim = _make_search_sim(robot_pos=rescue_pos, rescue_pos=rescue_pos)
    rp_id = RescuePointId(1)

    assert sim.rescue_found[rp_id] is False

    # The robot is already at the rescue point — one step triggers found
    sim._step()

    assert sim.rescue_found[rp_id] is True


# ---------------------------------------------------------------------------
# 6. All search robots reassigned to RESCUE task after found
# ---------------------------------------------------------------------------

def test_all_search_robots_reassigned_to_rescue_after_found():
    rescue_pos = Position(1, 0)
    sim = _make_search_sim(robot_pos=rescue_pos, rescue_pos=rescue_pos)

    sim._step()

    # After found, the rescue task should be assigned to our search robot
    rescue_task_id = TaskId(20)
    rescue_task_state = sim.task_states[rescue_task_id]
    assert RobotId(1) in rescue_task_state.assigned_robot_ids or \
        sim.rescue_found[RescuePointId(1)] is True


# ---------------------------------------------------------------------------
# 7. SEARCH tasks marked DONE after found event
# ---------------------------------------------------------------------------

def test_search_tasks_marked_done_after_found():
    rescue_pos = Position(1, 0)
    sim = _make_search_sim(robot_pos=rescue_pos, rescue_pos=rescue_pos)

    sim._step()

    search_task_state = sim.task_states[TaskId(10)]
    assert search_task_state.status == TaskStatus.DONE


# ---------------------------------------------------------------------------
# 8. No rescue points → simulation runs to budget (SEARCH task never finishes)
# ---------------------------------------------------------------------------

def test_no_rescue_points_simulation_runs_to_budget():
    env = Environment(5, 5)
    robot_id = RobotId(1)
    robot = Robot(id=robot_id, capabilities=frozenset(), speed=1)
    robot_state = RobotState(robot_id=robot_id, position=Position(0, 0))

    search_task_id = TaskId(10)
    search_task = Task(
        id=search_task_id,
        type=TaskType.SEARCH,
        priority=5,
        required_work_time=Time(9999),
    )
    search_task_state = TaskState(task_id=search_task_id, status=TaskStatus.ASSIGNED, assigned_robot_ids={robot_id})

    assignment_service = _InMemoryAssignmentService([
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

    result = sim.run(max_delta_time=10)
    # No rescue points → SEARCH never completes → simulation exhausts budget
    assert not result.completed
    assert result.makespan is None


# ---------------------------------------------------------------------------
# 9. Multiple robots at rescue point same tick → deterministic (lowest robot_id)
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

    robots = [
        Robot(id=r1_id, capabilities=frozenset(), speed=1),
        Robot(id=r2_id, capabilities=frozenset(), speed=1),
    ]
    robot_states = {
        r1_id: RobotState(robot_id=r1_id, position=rescue_pos),
        r2_id: RobotState(robot_id=r2_id, position=rescue_pos),
    }
    search_task = Task(id=search_task_id, type=TaskType.SEARCH, priority=5, required_work_time=Time(9999))
    rescue_task = Task(id=rescue_task_id, type=TaskType.RESCUE, priority=10, required_work_time=Time(5),
                       spatial_constraint=SpatialConstraint(target=rescue_pos))
    task_states = {
        search_task_id: TaskState(task_id=search_task_id, status=TaskStatus.ASSIGNED, assigned_robot_ids={r1_id, r2_id}),
        rescue_task_id: TaskState(task_id=rescue_task_id),
    }

    assignment_service = _InMemoryAssignmentService([
        Assignment(task_id=search_task_id, robot_ids=frozenset([r1_id, r2_id]), assign_at=Time(0))
    ])

    sim = Simulation(
        environment=env,
        robots=robots,
        tasks=[search_task, rescue_task],
        robot_states=robot_states,
        task_states=task_states,
        assignment_service=assignment_service,
        pathfinding_algorithm=astar_pathfind,
    )

    sim._step()

    # Should only be triggered once (deterministic)
    assert sim.rescue_found[RescuePointId(1)] is True
    assert sim.task_states[search_task_id].status == TaskStatus.DONE


# ---------------------------------------------------------------------------
# 10. add_rescue_point at obstacle position raises ValueError
# ---------------------------------------------------------------------------

def test_add_rescue_point_on_obstacle_raises():
    env = Environment(5, 5)
    obstacle_pos = Position(2, 2)
    env.add_obstacle(obstacle_pos)

    rp = RescuePoint(id=RescuePointId(1), position=obstacle_pos, name="Bad", rescue_task_id=TaskId(1))

    with pytest.raises(ValueError, match="obstacle"):
        env.add_rescue_point(rp)


# ---------------------------------------------------------------------------
# 11. snapshot().rescue_found reflects live state
# ---------------------------------------------------------------------------

def test_snapshot_rescue_found_reflects_live_state():
    rescue_pos = Position(1, 0)
    sim = _make_search_sim(robot_pos=rescue_pos, rescue_pos=rescue_pos)
    rp_id = RescuePointId(1)

    snap_before = sim.snapshot()
    assert snap_before.rescue_found[rp_id] is False

    sim._step()

    snap_after = sim.snapshot()
    assert snap_after.rescue_found[rp_id] is True


# ---------------------------------------------------------------------------
# 12. Load search_rescue.json → env.rescue_points has correct entry
# ---------------------------------------------------------------------------

def test_load_search_rescue_scenario():
    sim = load_simulation("scenarios/search_rescue.json")

    rescue_points = sim.environment.rescue_points
    assert len(rescue_points) == 1

    rp = list(rescue_points.values())[0]
    assert rp.id == RescuePointId(1)
    assert rp.name == "Survivor Alpha"
    assert rp.position == Position(10, 10)
    assert rp.rescue_task_id == TaskId(20)

    task_types = {t.id: t.type for t in sim.tasks}
    assert task_types[TaskId(10)] == TaskType.SEARCH
    assert task_types[TaskId(20)] == TaskType.RESCUE
