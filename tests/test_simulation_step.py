"""Integration tests for Simulation.step() with pathfinding."""

from __future__ import annotations

import math

from simulation_models.assignment import Assignment, RobotId
from simulation_models.capability import Capability
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.task import SpatialConstraint, Task, TaskId, TaskType
from simulation_models.task_state import TaskState, TaskStatus
from simulation_models.time import Time
from simulation_models.simulation import Simulation
from pathfinding_algorithms import bfs_pathfind


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_assign(tasks: list[Task], robots: list[Robot]) -> list[Assignment]:
    """1:1 greedy assignment by list order."""
    assignments: list[Assignment] = []
    used: set[RobotId] = set()
    for task in tasks:
        for robot in robots:
            if robot.id not in used:
                assignments.append(
                    Assignment(task_id=task.id, robot_ids=frozenset([robot.id]))
                )
                used.add(robot.id)
                break
    return assignments


def _make_sim(
    width: int = 10,
    height: int = 10,
    robots: list[Robot] | None = None,
    tasks: list[Task] | None = None,
    robot_states: dict[RobotId, RobotState] | None = None,
    task_states: dict[TaskId, TaskState] | None = None,
    obstacles: list[Position] | None = None,
) -> Simulation:
    env = Environment(width=width, height=height)
    for obs in (obstacles or []):
        env.add_obstacle(obs)

    robots = robots or []
    tasks = tasks or []
    robot_states = robot_states or {}
    task_states = task_states or {}

    sim = Simulation(
        environment=env,
        robots=robots,
        tasks=tasks,
        robot_states=robot_states,
        task_states=task_states,
        assignment_algorithm=_simple_assign,
        pathfinding_algorithm=bfs_pathfind,
    )
    return sim


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStepValidation:
    def test_step_raises_without_pathfinding_algorithm(self) -> None:
        sim = _make_sim()
        sim.pathfinding_algorithm = None
        try:
            sim.step()
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "pathfinding_algorithm" in str(e)


class TestCollisionAvoidance:
    def test_two_robots_head_on_never_overlap(self) -> None:
        """Two robots moving towards each other should never share a cell."""
        r1 = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
        r2 = Robot(id=RobotId(2), capabilities=frozenset(), speed=1.0)
        t1 = Task(
            id=TaskId(1), type=TaskType.PICKUP, priority=1,
            required_work_time=Time(1),
            spatial_constraint=SpatialConstraint(target=Position(9, 0)),
        )
        t2 = Task(
            id=TaskId(2), type=TaskType.PICKUP, priority=1,
            required_work_time=Time(1),
            spatial_constraint=SpatialConstraint(target=Position(0, 0)),
        )
        rs = {
            RobotId(1): RobotState.from_position(RobotId(1), Position(0, 0)),
            RobotId(2): RobotState.from_position(RobotId(2), Position(9, 0)),
        }
        ts = {
            TaskId(1): TaskState(task_id=TaskId(1)),
            TaskId(2): TaskState(task_id=TaskId(2)),
        }
        sim = _make_sim(
            robots=[r1, r2], tasks=[t1, t2],
            robot_states=rs, task_states=ts,
        )
        for _ in range(15):
            sim.step()
            positions = [s.position for s in sim.robot_states.values()]
            assert len(set(positions)) == len(positions), (
                f"Collision at tick {sim.t_now.tick}: {positions}"
            )


class TestBoundsAndObstacles:
    def test_robot_never_steps_out_of_bounds(self) -> None:
        r1 = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
        t1 = Task(
            id=TaskId(1), type=TaskType.PICKUP, priority=1,
            required_work_time=Time(1),
            spatial_constraint=SpatialConstraint(target=Position(4, 4)),
        )
        sim = _make_sim(
            width=5, height=5,
            robots=[r1],
            tasks=[t1],
            robot_states={RobotId(1): RobotState.from_position(RobotId(1), Position(0, 0))},
            task_states={TaskId(1): TaskState(task_id=TaskId(1))},
        )
        for _ in range(20):
            sim.step()
            pos = sim.robot_states[RobotId(1)].position
            assert sim.environment.in_bounds(pos), f"Out of bounds: {pos}"

    def test_robot_never_lands_on_obstacle(self) -> None:
        r1 = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
        t1 = Task(
            id=TaskId(1), type=TaskType.PICKUP, priority=1,
            required_work_time=Time(1),
            spatial_constraint=SpatialConstraint(target=Position(4, 0)),
        )
        obstacles = [Position(2, 0), Position(2, 1)]
        sim = _make_sim(
            width=5, height=5,
            robots=[r1],
            tasks=[t1],
            robot_states={RobotId(1): RobotState.from_position(RobotId(1), Position(0, 0))},
            task_states={TaskId(1): TaskState(task_id=TaskId(1))},
            obstacles=obstacles,
        )
        obs_set = sim.environment.obstacles
        for _ in range(20):
            sim.step()
            pos = sim.robot_states[RobotId(1)].position
            assert pos not in obs_set, f"Robot on obstacle: {pos}"


class TestWorkCompletion:
    def test_robot_reaches_goal_and_completes_work(self) -> None:
        """Robot 3 steps away with work_time=5 should finish in 3+5=8 ticks."""
        r1 = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
        t1 = Task(
            id=TaskId(1), type=TaskType.PICKUP, priority=1,
            required_work_time=Time(5),
            spatial_constraint=SpatialConstraint(target=Position(3, 0)),
        )
        sim = _make_sim(
            width=10, height=10,
            robots=[r1],
            tasks=[t1],
            robot_states={RobotId(1): RobotState.from_position(RobotId(1), Position(0, 0))},
            task_states={TaskId(1): TaskState(task_id=TaskId(1))},
        )
        for _ in range(8):
            sim.step()
        assert sim.task_states[TaskId(1)].status == TaskStatus.DONE


class TestIdleRobot:
    def test_unassigned_robot_stays_put(self) -> None:
        """Robot with no task assignment should idle and not move."""
        r1 = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
        start = Position(3, 3)
        sim = _make_sim(
            robots=[r1],
            tasks=[],
            robot_states={RobotId(1): RobotState.from_position(RobotId(1), start)},
            task_states={},
        )
        for _ in range(5):
            sim.step()
        assert sim.robot_states[RobotId(1)].position == start


class TestNoSpatialConstraint:
    def test_task_without_spatial_constraint_gets_work(self) -> None:
        r1 = Robot(id=RobotId(1), capabilities=frozenset(), speed=1.0)
        t1 = Task(
            id=TaskId(1), type=TaskType.ROUTINE_INSPECTION, priority=1,
            required_work_time=Time(3),
            spatial_constraint=None,
        )
        start = Position(2, 2)
        sim = _make_sim(
            robots=[r1],
            tasks=[t1],
            robot_states={RobotId(1): RobotState.from_position(RobotId(1), start)},
            task_states={TaskId(1): TaskState(task_id=TaskId(1))},
        )
        for _ in range(3):
            sim.step()
        assert sim.task_states[TaskId(1)].status == TaskStatus.DONE
        # Robot should not have moved
        assert sim.robot_states[RobotId(1)].position == start
