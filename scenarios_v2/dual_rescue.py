"""
Scenario: dual_rescue

A 24×16 map with two casualties hidden on opposite sides.  Two searchers
run simultaneously; each discovers their casualty and then teams up with a
dedicated carrier to extract it.  Both carry operations run in parallel.

Phases:
1. Search  — Robots 1 & 2 are assigned to the shared SearchTask.
             Robot 1 starts adjacent to Casualty A (left side).
             Robot 2 starts adjacent to Casualty B (right side).
             Both proximity locks fire on tick 1; both casualties are
             discovered on tick 2.

2. Split   — Discovery of Rescue Point A triggers assignment of Robots 1 & 3
             to MOVE_TASK_A.  Discovery of Rescue Point B triggers assignment
             of Robots 2 & 4 to MOVE_TASK_B.

3. Extract — Robot 1 is already in formation; Robot 3 travels up from the
             south to join.  Mirrored on the right side for Robot 2 & 4.
             Both formations carry their casualties to the extraction zones
             in the top corners simultaneously.

Layout (24×16):

  Extraction A (1,1)                    Extraction B (22,1)
      ↑                                         ↑
  Casualty A (4,8)  [rubble]  [center]  [rubble]  Casualty B (19,8)

  Robot 3 (4,14)                              Robot 4 (19,14)

Robot 1 (3,8) — adjacent to Casualty A (west)
Robot 2 (20,8) — adjacent to Casualty B (east)

Obstacle layout:
- Rubble A: northeast of casualty A, forces Robot 3 to approach from below
- Rubble B: northwest of casualty B, forces Robot 4 to approach from below
- Central cluster: visual separation between the two operation zones

Expected outcome: both MOVE_TASK_A_ID and MOVE_TASK_B_ID completed.
"""

from __future__ import annotations

from simulation.algorithms import astar_pathfind
from simulation.domain import (
    Environment, MoveTask, MoveTaskState, RescuePoint, Robot, RobotId, RobotState,
    SearchTask, TaskId, SpatialConstraint,
)
from simulation.domain.search_task import SearchTaskState
from simulation.primitives import Capability, Position, Time
from simulation.engine_rewrite import Assignment, SimulationRunner, SimulationState, StepOutcome
from simulation.engine_rewrite.services import (
    BaseAssignmentService, InMemoryAssignmentService,
    InMemorySimulationRegistry, InMemorySimulationStateService,
)


SEARCH_TASK_ID    = TaskId(1)   # shared — both searchers assigned here
RESCUE_POINT_A_ID = TaskId(2)   # discovery marker for casualty A
RESCUE_POINT_B_ID = TaskId(3)   # discovery marker for casualty B
MOVE_TASK_A_ID    = TaskId(4)   # carry casualty A to extraction A
MOVE_TASK_B_ID    = TaskId(5)   # carry casualty B to extraction B

ROBOT_IDS = [RobotId(1), RobotId(2), RobotId(3), RobotId(4)]

_WIDTH  = 24
_HEIGHT = 16

_CASUALTY_A_POS   = Position(4, 8)    # left-center
_CASUALTY_B_POS   = Position(19, 8)   # right-center
_EXTRACTION_A_POS = Position(1, 1)    # top-left corner
_EXTRACTION_B_POS = Position(22, 1)   # top-right corner

# Robot 1: searcher A — starts 1 cell west of casualty A; lock fires tick 1.
# Robot 2: searcher B — starts 1 cell east of casualty B; lock fires tick 1.
# Robots 3, 4: carriers — start south and travel north to join their formation.
_ROBOT_STARTS = {
    RobotId(1): Position(3, 8),    # adjacent to casualty A
    RobotId(2): Position(20, 8),   # adjacent to casualty B
    RobotId(3): Position(4, 14),   # carrier for team A
    RobotId(4): Position(19, 14),  # carrier for team B
}

# Obstacles — two rubble piles flanking the casualties + central separator.
_OBSTACLES = [
    # Rubble near casualty A — blocks direct northern approach for Robot 3
    Position(5, 6), Position(6, 6),
    Position(5, 7),
    # Rubble near casualty B — blocks direct northern approach for Robot 4
    Position(17, 6), Position(18, 6),
    Position(18, 7),
    # Central cluster — visual separation, does not block either team
    Position(11, 5), Position(12, 5),
    Position(11, 6), Position(12, 6),
]


def build(
    assignment_service: BaseAssignmentService | None = None,
) -> tuple[SimulationRunner, BaseAssignmentService]:
    env = Environment(width=_WIDTH, height=_HEIGHT)
    for pos in _OBSTACLES:
        env.add_obstacle(pos)

    # Two rescue points — proximity lock radius 1 so adjacent robots discover.
    rescue_a = RescuePoint(
        id=RESCUE_POINT_A_ID,
        priority=10,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(
            target=_CASUALTY_A_POS,
            max_distance=1,
        ),
        required_capabilities=frozenset({Capability.VISION}),
    )
    rescue_b = RescuePoint(
        id=RESCUE_POINT_B_ID,
        priority=10,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(
            target=_CASUALTY_B_POS,
            max_distance=1,
        ),
        required_capabilities=frozenset({Capability.VISION}),
    )
    env.add_rescue_point(rescue_a)
    env.add_rescue_point(rescue_b)

    search = SearchTask(
        id=SEARCH_TASK_ID,
        priority=5,
        required_capabilities=frozenset({Capability.VISION}),
    )

    # Both MoveTasks pre-staged at their casualty positions. Unassigned
    # until the corresponding rescue point is discovered.
    move_a = MoveTask(
        id=MOVE_TASK_A_ID,
        priority=8,
        destination=_EXTRACTION_A_POS,
        min_robots_required=2,
        min_distance=1,
    )
    move_b = MoveTask(
        id=MOVE_TASK_B_ID,
        priority=8,
        destination=_EXTRACTION_B_POS,
        min_robots_required=2,
        min_distance=1,
    )

    registry = InMemorySimulationRegistry()
    state_service = InMemorySimulationStateService()
    # Both searchers start on the shared SearchTask; carriers are idle.
    initial = [
        Assignment(task_id=SEARCH_TASK_ID, robot_id=RobotId(1)),
        Assignment(task_id=SEARCH_TASK_ID, robot_id=RobotId(2)),
    ]
    if assignment_service is None:
        assignment_service = InMemoryAssignmentService(assignments=initial)
    else:
        assignment_service.update(initial)
    runner = SimulationRunner(
        environment=env,
        registry=registry,
        state_service=state_service,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )
    for robot_id in ROBOT_IDS:
        runner.add_robot(
            Robot(id=robot_id, capabilities=frozenset({Capability.VISION})),
            RobotState(robot_id=robot_id, position=_ROBOT_STARTS[robot_id]),
        )
    runner.add_task(search, SearchTaskState(task_id=SEARCH_TASK_ID))
    runner.add_task(move_a, MoveTaskState(task_id=MOVE_TASK_A_ID, current_position=_CASUALTY_A_POS))
    runner.add_task(move_b, MoveTaskState(task_id=MOVE_TASK_B_ID, current_position=_CASUALTY_B_POS))
    return runner, assignment_service


def run(max_ticks: int = 400) -> tuple[SimulationState, list[StepOutcome], SimulationRunner]:
    runner, assignment_service = build()
    outcomes: list[StepOutcome] = []

    for _ in range(max_ticks):
        state, outcome = runner.step()
        outcomes.append(outcome)

        for task, _ in outcome.tasks_spawned:
            if isinstance(task, RescuePoint) and task.id == RESCUE_POINT_A_ID:
                assignment_service.update([
                    Assignment(task_id=MOVE_TASK_A_ID, robot_id=RobotId(1)),
                    Assignment(task_id=MOVE_TASK_A_ID, robot_id=RobotId(3)),
                ])
            elif isinstance(task, RescuePoint) and task.id == RESCUE_POINT_B_ID:
                assignment_service.update([
                    Assignment(task_id=MOVE_TASK_B_ID, robot_id=RobotId(2)),
                    Assignment(task_id=MOVE_TASK_B_ID, robot_id=RobotId(4)),
                ])

        if (
            MOVE_TASK_A_ID in outcome.tasks_completed
            and MOVE_TASK_B_ID in outcome.tasks_completed
        ):
            break

    return state, outcomes, runner


if __name__ == "__main__":
    import os
    import time

    from simulation_view.terminal_renderer import TerminalRenderer
    from simulation_view.v2.view import SimulationViewV2

    runner, assignment_service = build()
    view = SimulationViewV2()
    renderer = TerminalRenderer()
    outcomes: list[StepOutcome] = []

    try:
        for _ in range(400):
            state, outcome = runner.step()
            outcomes.append(outcome)

            for task, _ in outcome.tasks_spawned:
                if isinstance(task, RescuePoint) and task.id == RESCUE_POINT_A_ID:
                    assignment_service.update([
                        Assignment(task_id=MOVE_TASK_A_ID, robot_id=RobotId(1)),
                        Assignment(task_id=MOVE_TASK_A_ID, robot_id=RobotId(3)),
                    ])
                elif isinstance(task, RescuePoint) and task.id == RESCUE_POINT_B_ID:
                    assignment_service.update([
                        Assignment(task_id=MOVE_TASK_B_ID, robot_id=RobotId(2)),
                        Assignment(task_id=MOVE_TASK_B_ID, robot_id=RobotId(4)),
                    ])

            terminal = os.get_terminal_size()
            frame = view.render(state, width=terminal.columns, height=terminal.lines)
            renderer.draw(frame)

            if (
                MOVE_TASK_A_ID in outcome.tasks_completed
                and MOVE_TASK_B_ID in outcome.tasks_completed
            ):
                time.sleep(1.0)
                break

            time.sleep(0.1)
    finally:
        renderer.cleanup()

    final_positions = {
        robot_id: rs.position
        for robot_id, rs in state.robot_states.items()
    }
    move_a_state = state.task_states.get(MOVE_TASK_A_ID)
    move_b_state = state.task_states.get(MOVE_TASK_B_ID)

    print(runner.report())
    print(f"Final robot positions: {final_positions}")
    print(f"Final position casualty A: {getattr(move_a_state, 'current_position', '?')}")
    print(f"Final position casualty B: {getattr(move_b_state, 'current_position', '?')}")
