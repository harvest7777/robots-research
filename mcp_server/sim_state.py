"""
Live simulation singleton for the MCP server.

Holds a single Simulation instance (the "live" sim) that MCP tools read from
and write to. Also provides fork_sim() for hypothetical evaluation runs that
do not affect the live sim.
"""

import dataclasses

from pathfinding_algorithms.astar_pathfinding import astar_pathfind
from simulation_models.assignment import Assignment, RobotId
from simulation_models.capability import Capability
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.simulation import Simulation
from simulation_models.task import SpatialConstraint, Task, TaskId, TaskType
from simulation_models.task_state import TaskState
from simulation_models.time import Time
from simulation_models.zone import Zone, ZoneId, ZoneType


def _build_default_scenario() -> Simulation:
    """Build a small warehouse scenario used as the live simulation."""
    env = Environment(width=12, height=12)

    # A wall of obstacles to make pathfinding non-trivial
    for y in range(3, 7):
        env.add_obstacle(Position(5.0, float(y)))

    # Loading zone (top-left corner)
    env.add_zone(
        Zone.from_positions(
            ZoneId(1),
            ZoneType.LOADING,
            [Position(float(x), float(y)) for x in range(3) for y in range(3)],
        )
    )

    # Charging zone (bottom-right corner)
    env.add_zone(
        Zone.from_positions(
            ZoneId(2),
            ZoneType.CHARGING,
            [Position(float(x), float(y)) for x in range(9, 12) for y in range(9, 12)],
        )
    )

    r1_id, r2_id, r3_id = RobotId(1), RobotId(2), RobotId(3)

    robots = [
        Robot(
            id=r1_id,
            capabilities=frozenset({Capability.MANIPULATION, Capability.VISION}),
            speed=1.0,
        ),
        Robot(
            id=r2_id,
            capabilities=frozenset({Capability.MANIPULATION}),
            speed=1.2,
        ),
        Robot(
            id=r3_id,
            capabilities=frozenset({Capability.VISION, Capability.SENSING}),
            speed=0.8,
        ),
    ]

    robot_states = {
        r1_id: RobotState(robot_id=r1_id, position=Position(0.0, 0.0)),
        r2_id: RobotState(robot_id=r2_id, position=Position(1.0, 0.0)),
        r3_id: RobotState(robot_id=r3_id, position=Position(0.0, 1.0)),
    }

    t1_id, t2_id = TaskId(1), TaskId(2)

    tasks = [
        Task(
            id=t1_id,
            type=TaskType.PICKUP,
            priority=3,
            required_work_time=Time(20),
            spatial_constraint=SpatialConstraint(target=Position(9.0, 9.0)),
            required_capabilities=frozenset({Capability.MANIPULATION}),
        ),
        Task(
            id=t2_id,
            type=TaskType.ROUTINE_INSPECTION,
            priority=1,
            required_work_time=Time(15),
            spatial_constraint=SpatialConstraint(target=Position(7.0, 2.0)),
            required_capabilities=frozenset({Capability.VISION}),
        ),
    ]

    task_states = {
        t1_id: TaskState(task_id=t1_id),
        t2_id: TaskState(task_id=t2_id),
    }

    def noop_assign(tasks, robots):
        return []

    return Simulation(
        environment=env,
        robots=robots,
        tasks=tasks,
        robot_states=robot_states,
        task_states=task_states,
        assignment_algorithm=noop_assign,
        pathfinding_algorithm=astar_pathfind,
    )


# Module-level live simulation singleton
_live_sim: Simulation = _build_default_scenario()


def get_live_sim() -> Simulation:
    """Return the module-level live simulation instance."""
    return _live_sim


def fork_sim(assignments: list[Assignment]) -> Simulation:
    """
    Return a deep copy of the live sim with the given assignments locked in.

    The fork's assignment algorithm always returns the provided assignments,
    ignoring the live sim's current algorithm. Stepping the fork does NOT
    affect the live sim.
    """
    live = get_live_sim()

    robot_states_copy = {
        rid: dataclasses.replace(state) for rid, state in live.robot_states.items()
    }

    task_states_copy = {
        tid: TaskState(
            task_id=state.task_id,
            status=state.status,
            assigned_robot_ids=set(state.assigned_robot_ids),
            work_done=state.work_done,
            started_at=state.started_at,
            completed_at=state.completed_at,
        )
        for tid, state in live.task_states.items()
    }

    fixed = list(assignments)

    return Simulation(
        environment=live.environment,
        robots=list(live.robots),
        tasks=list(live.tasks),
        robot_states=robot_states_copy,
        task_states=task_states_copy,
        assignment_algorithm=lambda tasks, robots: fixed,
        pathfinding_algorithm=live.pathfinding_algorithm,
        t_now=live.t_now,
    )
