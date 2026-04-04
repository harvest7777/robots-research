# Scenario 13 — Formation Requirement (MoveTask)
#
# Two cargo objects that must be physically carried to their destinations.
# Each requires 3 robots within min_distance=1 to form a quorum and move.
# With only 5 robots total, both formations cannot run simultaneously.
#
# Tasks:
# - T1_CARGO_A: top lane cargo,    (3,4)  → (25,4),  min_robots_required=3
# - T2_CARGO_B: bottom lane cargo, (3,10) → (25,10), min_robots_required=3

from __future__ import annotations

from experiments.models.task_spawn import SpawnTask
from simulation.domain import TaskId, MoveTask, MoveTaskState
from simulation.primitives import Position

T1_CARGO_A = TaskId(1)
T2_CARGO_B = TaskId(2)

TASK_SPAWNS = [
    SpawnTask(
        task_to_spawn=MoveTask(
            id=T1_CARGO_A,
            priority=1,
            min_robots_required=3,
            min_distance=1,
            destination=Position(25, 4),
        ),
        task_state=MoveTaskState(task_id=T1_CARGO_A, current_position=Position(3, 4)),
    ),
    SpawnTask(
        task_to_spawn=MoveTask(
            id=T2_CARGO_B,
            priority=1,
            min_robots_required=3,
            min_distance=1,
            destination=Position(25, 10),
        ),
        task_state=MoveTaskState(task_id=T2_CARGO_B, current_position=Position(3, 10)),
    ),
]
