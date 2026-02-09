"""
Read-only snapshot of simulation state.

This module provides `SimulationSnapshot`, an immutable point-in-time view of
the simulation state. The view layer should depend only on snapshots, not on
the live `Simulation` object.

Immutability guarantees:
- `SimulationSnapshot` is a frozen dataclass.
- Robot and task lists are tuples (immutable sequences).
- State mappings are wrapped in `MappingProxyType` (read-only dict views).
- State objects are copies, isolated from the live simulation.

Note: `RobotState` and `TaskState` objects within the snapshot are copies but
remain technically mutable dataclasses. Modifying them will not affect the live
simulation, but callers should treat them as read-only by convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from simulation_models.assignment import RobotId
    from simulation_models.environment import Environment
    from simulation_models.robot import Robot
    from simulation_models.robot_state import RobotState
    from simulation_models.task import Task, TaskId
    from simulation_models.task_state import TaskState
    from simulation_models.time import Time


@dataclass(frozen=True)
class SimulationSnapshot:
    """
    Immutable, point-in-time view of simulation state.

    This snapshot captures the complete state of a simulation at a specific moment.
    It is designed for read-only consumption by view layers, analytics, or logging.

    Attributes:
        env: The environment (grid, zones, obstacles).
        robots: Tuple of robot definitions (immutable).
        robot_states: Read-only mapping of robot ID to runtime state (copies).
        tasks: Tuple of task definitions (immutable).
        task_states: Read-only mapping of task ID to runtime state (copies).
        t_now: Current simulation time, if tracked. None otherwise.
    """

    env: "Environment"
    robots: tuple["Robot", ...]
    robot_states: Mapping["RobotId", "RobotState"]
    tasks: tuple["Task", ...]
    task_states: Mapping["TaskId", "TaskState"]
    t_now: "Time | None" = None


if __name__ == "__main__":
    # Minimal demonstration: construct a simulation, step, and view history.
    from simulation_models.assignment import Assignment, RobotId
    from simulation_models.capability import Capability
    from simulation_models.environment import Environment
    from simulation_models.position import Position
    from simulation_models.robot import Robot
    from simulation_models.robot_state import RobotState
    from simulation_models.simulation import Simulation
    from simulation_models.task import Task, TaskId, TaskType, SpatialConstraint
    from simulation_models.task_state import TaskState
    from simulation_models.time import Time

    # Create a small environment
    env = Environment(width=5, height=5)

    # Create one robot
    robot_id = RobotId(1)
    robot = Robot(
        id=robot_id,
        capabilities=frozenset({Capability.VISION}),
        speed=1.0,
    )
    robot_state = RobotState.from_position(robot_id, Position(0, 0))

    # Create one task
    task_id = TaskId(1)
    task = Task(
        id=task_id,
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(2, 2)),
    )
    task_state = TaskState(task_id=task_id)

    # Build simulation with a no-op assignment algorithm
    def noop_assign(tasks: list, robots: list) -> list[Assignment]:
        return []

    sim = Simulation(
        environment=env,
        robots=[robot],
        tasks=[task],
        robot_states={robot_id: robot_state},
        task_states={task_id: task_state},
        assignment_algorithm=noop_assign,
    )

    # Run a few steps
    print("=== SimulationSnapshot History Demo ===")
    print(f"Initial history has {len(sim.history)} snapshot(s) at t={sim.t_now.tick}")

    for _ in range(3):
        sim.step()
        print(f"After step: t_now={sim.t_now.tick}, history size={len(sim.history)}")

    # Iterate through history
    print("\n--- History ---")
    for t, snap in sorted(sim.history.items(), key=lambda x: x[0].tick):
        r_state = snap.robot_states[robot_id]
        t_state = snap.task_states[task_id]
        print(f"t={t.tick}: robot at ({r_state.x}, {r_state.y}), task status={t_state.status.value}")

    # Verify snapshot isolation
    initial_snap = sim.history[Time(0)]
    original_x = initial_snap.robot_states[robot_id].x
    sim.robot_states[robot_id].x = 999.0
    assert initial_snap.robot_states[robot_id].x == original_x, "Snapshot should be isolated!"
    print("\n[OK] Snapshots are isolated from live simulation.")
