"""
Integration test: formation approach deadlock.

Three robots start in a horizontal line to the left of a MoveTask.  All
three are assigned to the task from tick 0.  The first robot to arrive
parks at (task_x - 1, y) — the nearest adjacent slot.  The second and
third robots then try to pathfind straight through that occupied cell and
get permanently blocked, even though (task_x, y±1) are open slots they
could reach by going around.

Grid (20×5, no obstacles):

    . . . . . . . . . . . . . . . T . . . .   row 0
    . . . . . . . . . . . . . . . T . . . .   row 1
    . R1. R2. R3. . . . . . . . . T . . . .   row 2  (T = task at x=15)
    . . . . . . . . . . . . . . . T . . . .   row 3
    . . . . . . . . . . . . . . . T . . . .   row 4

(T marks the column only for illustration — the task is a single cell.)

R1 @ (3, 2), R2 @ (4, 2), R3 @ (5, 2).  Task @ (15, 2) → dest (2, 2).
min_robots_required=2, min_distance=1.

Expected: the task completes — at least two robots fan out around the
task and carry it to the destination.  With the pathfinding bug, R3
parks at (14, 2) and R2 / R1 never reach an adjacent slot, so the task
never moves.
"""

import pytest
from simulation.algorithms import astar_pathfind
from simulation.domain import Environment, MoveTask, MoveTaskState, Robot, RobotId, RobotState, TaskId
from simulation.engine_rewrite import Assignment, SimulationRunner
from simulation.engine_rewrite.services import InMemoryAssignmentService, InMemorySimulationStore
from simulation.primitives import Position

_TASK_ID = TaskId(1)
_R1, _R2, _R3 = RobotId(1), RobotId(2), RobotId(3)

_TASK_START = Position(15, 2)
_TASK_DEST  = Position(2, 2)

_WIDTH  = 20
_HEIGHT = 5


def _build() -> SimulationRunner:
    task = MoveTask(
        id=_TASK_ID,
        priority=5,
        destination=_TASK_DEST,
        min_robots_required=2,
        min_distance=1,
    )
    store = InMemorySimulationStore()
    asgn  = InMemoryAssignmentService(assignments=[
        Assignment(task_id=_TASK_ID, robot_id=_R1),
        Assignment(task_id=_TASK_ID, robot_id=_R2),
        Assignment(task_id=_TASK_ID, robot_id=_R3),
    ])
    runner = SimulationRunner(
        environment=Environment(width=_WIDTH, height=_HEIGHT),
        store=store,
        assignment_service=asgn,
        pathfinding=astar_pathfind,
    )
    for rid, pos in [(_R1, Position(3, 2)), (_R2, Position(4, 2)), (_R3, Position(5, 2))]:
        store.add_robot(Robot(id=rid, capabilities=frozenset()), RobotState(robot_id=rid, position=pos))
    store.add_task(task, MoveTaskState(task_id=_TASK_ID, current_position=_TASK_START))
    return runner


@pytest.mark.xfail(reason="pathfinding ignores robot occupancy; inline robots deadlock approaching formation")
def test_formation_completes_despite_inline_approach():
    """Robots in a line must fan out around the task and complete the carry."""
    runner = _build()
    completed = False
    for _ in range(150):
        _, outcome = runner.step()
        if _TASK_ID in outcome.tasks_completed:
            completed = True
            break
    assert completed, "MoveTask never completed — robots deadlocked approaching the formation"
