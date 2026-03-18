"""
Scenario: search_and_rescue_move

A 20×20 rubble-strewn map. Robot 1 searches and discovers the casualty
on tick 1 (it starts adjacent). Discovery triggers reassignment of all
three robots to the pre-staged MoveTask; the carriers travel across the
rubble field from opposite corners to join the formation.

Phases:
1. Search  — Robot 1 starts adjacent to the casualty at (16, 14);
             proximity lock fires on tick 1 and discovery happens
             on tick 2 (after the robot steps onto the casualty cell).
2. Discovery — The rescue point spawns. The scenario loop reassigns all
             robots to the pre-staged MoveTask.
3. Extraction — Robot 1 is already in position; Robots 2 & 3 travel from
             (19, 18) and (19, 0) (right edge) to join the formation.
             Approaching from the east keeps them from blocking the
             westward carry. Once two robots are adjacent the formation
             moves the casualty to (2, 3).

Obstacle layout:
- Collapsed building: upper-center cluster (x=7..10, y=4..6)
- Debris pile: near casualty (x=13..15, y=12..13), forcing a southern approach

Expected outcome: MOVE_TASK_ID in tasks_completed before max_ticks.
"""

from __future__ import annotations

from simulation.algorithms.astar_pathfinding import astar_pathfind
from simulation.domain.environment import Environment
from simulation.domain.move_task import MoveTask, MoveTaskState
from simulation.domain.rescue_point import RescuePoint
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.search_task import SearchTask, SearchTaskState
from simulation.domain.base_task import TaskId
from simulation.domain.task import SpatialConstraint
from simulation.primitives.capability import Capability
from simulation.primitives.position import Position
from simulation.primitives.time import Time

from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.runner import SimulationRunner
from simulation.engine_rewrite.simulation_state import SimulationState
from simulation.engine_rewrite.services.base_assignment_service import BaseAssignmentService
from simulation.engine_rewrite.services.in_memory_assignment_service import InMemoryAssignmentService
from simulation.engine_rewrite.services.in_memory_task_registry import InMemoryTaskRegistry
from simulation.engine_rewrite.step_outcome import StepOutcome


SEARCH_TASK_ID  = TaskId(1)
RESCUE_POINT_ID = TaskId(2)   # discovery marker only — not worked by any robot
MOVE_TASK_ID    = TaskId(3)   # carry casualty to extraction

ROBOT_IDS = [RobotId(1), RobotId(2), RobotId(3)]

_WIDTH  = 20
_HEIGHT = 20

_CASUALTY_POS   = Position(16, 14)  # where the victim is hidden
_EXTRACTION_POS = Position(2, 3)    # safe zone, top-left

# Robot 1: searcher — starts one step west of casualty; proximity lock fires
#          immediately and discovery happens on tick 1.
# Robots 2 & 3: carriers — start on the right edge so they approach the
#          casualty from the east, keeping them behind the formation as it
#          travels west toward the extraction zone.
_ROBOT_STARTS = {
    RobotId(1): Position(15, 14),
    RobotId(2): Position(19, 18),
    RobotId(3): Position(19, 0),
}

# Obstacle layout — two rubble clusters.
_OBSTACLES = [
    # Collapsed building — upper-center, forces detour around y=4..6
    Position(7, 4),  Position(8, 4),  Position(9, 4),  Position(10, 4),
    Position(7, 5),  Position(9, 5),  Position(10, 5),
    Position(8, 6),  Position(9, 6),
    # Debris pile — near casualty, blocks direct northern approach
    Position(13, 12), Position(14, 12), Position(15, 12),
    Position(13, 13),
]


def build(
    assignment_service: BaseAssignmentService | None = None,
) -> tuple[SimulationRunner, BaseAssignmentService]:
    env = Environment(width=_WIDTH, height=_HEIGHT)
    for pos in _OBSTACLES:
        env.add_obstacle(pos)

    # Rescue point — discovery marker with proximity lock radius = 1.
    # Robot 1 starts adjacent, so the lock fires on tick 1 and discovery on tick 2.
    # No robot is ever assigned to work it; it only triggers the MoveTask handover.
    rescue = RescuePoint(
        id=RESCUE_POINT_ID,
        priority=10,
        required_work_time=Time(1),
        spatial_constraint=SpatialConstraint(
            target=_CASUALTY_POS,
            max_distance=1,
        ),
        required_capabilities=frozenset({Capability.VISION}),
    )
    env.add_rescue_point(rescue)

    search = SearchTask(
        id=SEARCH_TASK_ID,
        priority=5,
        required_capabilities=frozenset({Capability.VISION}),
    )

    # MoveTask is pre-staged at the casualty location.  Unassigned until discovery.
    move = MoveTask(
        id=MOVE_TASK_ID,
        priority=8,
        destination=_EXTRACTION_POS,
        min_robots_required=3,
        min_distance=1,
    )

    robots = {
        robot_id: Robot(id=robot_id, capabilities=frozenset({Capability.VISION}))
        for robot_id in ROBOT_IDS
    }
    robot_states = {
        robot_id: RobotState(robot_id=robot_id, position=pos)
        for robot_id, pos in _ROBOT_STARTS.items()
    }

    state = SimulationState(
        environment=env,
        robots=robots,
        robot_states=robot_states,
        tasks={SEARCH_TASK_ID: search, MOVE_TASK_ID: move},
        task_states={
            SEARCH_TASK_ID: SearchTaskState(
                task_id=SEARCH_TASK_ID, rescue_found=frozenset()
            ),
            MOVE_TASK_ID: MoveTaskState(
                task_id=MOVE_TASK_ID, current_position=_CASUALTY_POS
            ),
        },
        t_now=Time(0),
    )

    registry = InMemoryTaskRegistry(tasks=[search, move])
    # Only Robot 1 searches initially; carriers 2 & 3 are idle until discovery.
    initial = [Assignment(task_id=SEARCH_TASK_ID, robot_id=RobotId(1))]
    if assignment_service is None:
        assignment_service = InMemoryAssignmentService(assignments=initial)
    else:
        assignment_service.update(initial)
    runner = SimulationRunner(
        state=state,
        registry=registry,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )
    return runner, assignment_service


def run(max_ticks: int = 300) -> tuple[SimulationState, list[StepOutcome], SimulationRunner]:
    runner, assignment_service = build()
    outcomes: list[StepOutcome] = []

    for _ in range(max_ticks):
        state, outcome = runner.step()
        outcomes.append(outcome)

        # On discovery: reassign all three robots to carry the casualty out.
        for task in outcome.tasks_spawned:
            if isinstance(task, RescuePoint) and task.id == RESCUE_POINT_ID:
                assignment_service.update([
                    Assignment(task_id=MOVE_TASK_ID, robot_id=robot_id)
                    for robot_id in ROBOT_IDS
                ])

        if MOVE_TASK_ID in outcome.tasks_completed:
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
        for _ in range(300):
            state, outcome = runner.step()
            outcomes.append(outcome)

            for task in outcome.tasks_spawned:
                if isinstance(task, RescuePoint) and task.id == RESCUE_POINT_ID:
                    assignment_service.update([
                        Assignment(task_id=MOVE_TASK_ID, robot_id=robot_id)
                        for robot_id in ROBOT_IDS
                    ])

            terminal = os.get_terminal_size()
            frame = view.render(state, width=terminal.columns, height=terminal.lines)
            renderer.draw(frame)

            if MOVE_TASK_ID in outcome.tasks_completed:
                time.sleep(1.0)
                break

            time.sleep(0.1)
    finally:
        renderer.cleanup()

    discovery_tick = next(
        (i + 1 for i, o in enumerate(outcomes) if o.tasks_spawned),
        None,
    )
    final_positions = {
        robot_id: rs.position
        for robot_id, rs in state.robot_states.items()
    }
    move_state = state.task_states.get(MOVE_TASK_ID)

    print(runner.report())
    print(f"Casualty discovered at tick: {discovery_tick}")
    print(f"Final robot positions: {final_positions}")
    print(f"Final casualty position: {getattr(move_state, 'current_position', '?')}")
