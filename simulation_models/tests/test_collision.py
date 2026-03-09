"""
Collision resolution tests.

Verifies that no two robots share a cell after movement, including
edge cases like chain moves, swaps, and the cascade-cancellation bug
(a robot whose move is cancelled blocking a robot already granted that cell).
"""

from __future__ import annotations

from pathfinding_algorithms.astar_pathfinding import astar_pathfind
from services.base_assignment_service import BaseAssignmentService
from simulation_models.assignment import Assignment, RobotId
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.simulation import Simulation
from simulation_models.task import Task, TaskId, TaskType, SpatialConstraint
from simulation_models.task_state import TaskState, TaskStatus
from simulation_models.time import Time


class _StaticAssignmentService(BaseAssignmentService):
    def __init__(self, assignments: list[Assignment]) -> None:
        self._assignments = assignments

    def get_assignments_for_time(self, time: Time) -> list[Assignment]:
        return list(self._assignments)

    def set_assignments(self, assignments: list[Assignment]) -> None:
        self._assignments = list(assignments)

    def add_assignments(self, assignments: list[Assignment]) -> None:
        self._assignments.extend(assignments)


def _make_sim(
    positions: dict[RobotId, Position],
    goals: dict[RobotId, Position],
    env_size: int = 10,
) -> Simulation:
    """Build a minimal sim where each robot is assigned a task at its goal."""
    env = Environment(env_size, env_size)
    robots = [Robot(id=rid, capabilities=frozenset(), speed=1) for rid in positions]
    robot_states = {rid: RobotState(robot_id=rid, position=pos) for rid, pos in positions.items()}

    tasks = []
    task_states = []
    assignments = []
    for rid, goal in goals.items():
        tid = TaskId(rid)
        tasks.append(Task(
            id=tid,
            type=TaskType.ROUTINE_INSPECTION,
            priority=1,
            required_work_time=Time(100),
            spatial_constraint=SpatialConstraint(target=goal),
        ))
        task_states.append(TaskState(task_id=tid, status=TaskStatus.ASSIGNED, assigned_robot_ids={rid}))
        assignments.append(Assignment(task_id=tid, robot_ids=frozenset([rid]), assign_at=Time(0)))

    svc = _StaticAssignmentService(assignments)
    return Simulation(
        environment=env,
        robots=robots,
        tasks=tasks,
        robot_states={rid: robot_states[rid] for rid in positions},
        task_states={TaskId(rid): ts for rid, ts in zip(positions, task_states)},
        assignment_service=svc,
        pathfinding_algorithm=astar_pathfind,
    )


def _positions_after_step(sim: Simulation) -> dict[RobotId, Position]:
    sim._step()
    return {rid: state.position for rid, state in sim.robot_states.items()}


def _no_overlap(positions: dict[RobotId, Position]) -> bool:
    pos_list = list(positions.values())
    return len(pos_list) == len(set(pos_list))


# ---------------------------------------------------------------------------
# Basic: two robots heading for the same cell — lower id wins
# ---------------------------------------------------------------------------

def test_two_robots_same_target_lower_id_wins():
    # Both robots heading toward (5, 5): R1 from left, R2 from right
    r1, r2 = RobotId(1), RobotId(2)
    goal = Position(5, 5)
    sim = _make_sim(
        positions={r1: Position(4, 5), r2: Position(6, 5)},
        goals={r1: goal, r2: goal},
    )
    after = _positions_after_step(sim)
    assert _no_overlap(after), f"Overlap: {after}"
    # R1 has lower id — it should get the cell
    assert after[r1] == goal
    assert after[r2] == Position(6, 5)  # blocked, stays put


# ---------------------------------------------------------------------------
# Chain move: A → B's cell, B moves away — all three should succeed
# ---------------------------------------------------------------------------

def test_chain_move_no_collision():
    r1, r2 = RobotId(1), RobotId(2)
    # R1 at (3,5) wants (4,5); R2 at (4,5) wants (5,5)
    sim = _make_sim(
        positions={r1: Position(3, 5), r2: Position(4, 5)},
        goals={r1: Position(5, 5), r2: Position(6, 5)},
    )
    after = _positions_after_step(sim)
    assert _no_overlap(after), f"Overlap: {after}"
    assert after[r1] == Position(4, 5)
    assert after[r2] == Position(5, 5)


# ---------------------------------------------------------------------------
# Cascade cancellation bug: R1 moving to Q, R2 at Q gets blocked and "stays"
# ---------------------------------------------------------------------------

def test_cascade_cancellation_no_collision():
    # R1 at (3,5) → (4,5) [= R2's cell]
    # R2 at (4,5) → (5,5), but (5,5) is occupied by R3 who is NOT moving
    # Bug: R2 cancels and "stays" at (4,5), but R1 was already granted (4,5)
    r1, r2, r3 = RobotId(1), RobotId(2), RobotId(3)
    sim = _make_sim(
        positions={r1: Position(3, 5), r2: Position(4, 5), r3: Position(5, 5)},
        # R3's goal is its own cell (already there — won't move)
        goals={r1: Position(9, 5), r2: Position(9, 5), r3: Position(5, 5)},
    )
    after = _positions_after_step(sim)
    assert _no_overlap(after), f"Overlap after step: {after}"


# ---------------------------------------------------------------------------
# Swap: two robots swap cells — both moves are valid
# ---------------------------------------------------------------------------

def test_swap_both_robots_move():
    r1, r2 = RobotId(1), RobotId(2)
    sim = _make_sim(
        positions={r1: Position(4, 5), r2: Position(5, 5)},
        goals={r1: Position(5, 5), r2: Position(4, 5)},
    )
    after = _positions_after_step(sim)
    assert _no_overlap(after), f"Overlap: {after}"
    assert after[r1] == Position(5, 5)
    assert after[r2] == Position(4, 5)


# ---------------------------------------------------------------------------
# Many robots converging on one cell — only lowest id reaches it
# ---------------------------------------------------------------------------

def test_many_robots_converging_no_overlap():
    goal = Position(5, 5)
    robots = {
        RobotId(i): pos for i, pos in enumerate([
            Position(4, 5), Position(6, 5),
            Position(5, 4), Position(5, 6),
        ], start=1)
    }
    sim = _make_sim(positions=robots, goals={rid: goal for rid in robots})
    after = _positions_after_step(sim)
    assert _no_overlap(after), f"Overlap: {after}"
    # Exactly one robot at the goal
    assert sum(1 for p in after.values() if p == goal) == 1
