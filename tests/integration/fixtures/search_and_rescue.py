"""
Scenario: search_and_rescue

One robot is assigned to a search task. It starts adjacent to the rescue
point, so the proximity lock kicks in immediately and it discovers the rescue
point on tick 1.

The scenario loop reacts to the discovery by assigning all four robots to the
rescue task. The rescue point has max_distance=1, so robots can work from any
adjacent cell — they converge and form a ring around the target.

This exercises:
- Search task roaming and rescue point discovery
- Dynamic task assignment reacting to outcome.tasks_spawned
- Pathfinding for multiple robots converging on a shared spatial target
- Collision resolution as robots arrive from different directions
- Parallel work accumulation once robots are in position

Expected outcome:
- Rescue point is discovered on tick 1
- All 4 robots are assigned to the rescue task
- Rescue task completes
- All robots end within max_distance=1 of the rescue point
"""

from __future__ import annotations

from simulation.algorithms import astar_pathfind
from simulation.domain import (
    Environment, RescuePoint, Robot, RobotId, RobotState,
    SearchTask, TaskId, SpatialConstraint, WorkTask, TaskState,
)
from simulation.domain.search_task import SearchTaskState
from simulation.primitives import Capability, Position, Time
from simulation.engine_rewrite import Assignment, SimulationRunner, SimulationState, StepOutcome
from simulation.engine_rewrite.services import (
    BaseAssignmentService, InMemoryAssignmentService, InMemorySimulationStore,
)


SEARCH_TASK_ID  = TaskId(1)
RESCUE_POINT_ID = TaskId(2)
ROBOT_IDS       = [RobotId(1), RobotId(2), RobotId(3), RobotId(4)]

_RESCUE_POSITION   = Position(5, 5)
_RESCUE_MAX_DIST   = 1          # robots work from adjacent cells; forms a + shape
_RESCUE_WORK_TIME  = 30         # long enough that all 4 robots must contribute to finish

# Robot 1 starts adjacent to the rescue point — proximity lock fires on tick 1.
# Robots 2-4 start at the corners so pathfinding is exercised from afar.
_ROBOT_STARTS = {
    RobotId(1): Position(5, 4),   # one step south of rescue — discovers on tick 1
    RobotId(2): Position(0, 0),
    RobotId(3): Position(9, 0),
    RobotId(4): Position(9, 9),
}


def build() -> tuple[SimulationRunner, BaseAssignmentService]:
    _rescue_task = WorkTask(
        id=RESCUE_POINT_ID,
        priority=10,
        required_work_time=Time(_RESCUE_WORK_TIME),
        spatial_constraint=SpatialConstraint(
            target=_RESCUE_POSITION,
            max_distance=_RESCUE_MAX_DIST,
        ),
        required_capabilities=frozenset({Capability.VISION}),
    )
    rescue = RescuePoint(
        id=RESCUE_POINT_ID,
        name="",
        spatial_constraint=SpatialConstraint(
            target=_RESCUE_POSITION,
            max_distance=_RESCUE_MAX_DIST,
        ),
        task=_rescue_task,
        initial_task_state=TaskState(task_id=RESCUE_POINT_ID),
    )
    env = Environment(width=10, height=10)
    env.add_rescue_point(rescue)

    search = SearchTask(
        id=SEARCH_TASK_ID,
        priority=5,
        required_capabilities=frozenset({Capability.VISION}),
    )
    robots = [
        Robot(id=robot_id, capabilities=frozenset({Capability.VISION}))
        for robot_id in ROBOT_IDS
    ]

    store = InMemorySimulationStore()
    # Only robot 1 does the search — the others wait for a rescue assignment.
    assignment_service = InMemoryAssignmentService(
        assignments=[Assignment(task_id=SEARCH_TASK_ID, robot_id=RobotId(1))]
    )
    runner = SimulationRunner(
        environment=env,
        store=store,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )
    for robot in robots:
        store.add_robot(robot, RobotState(robot_id=robot.id, position=_ROBOT_STARTS[robot.id]))
    store.add_task(search, SearchTaskState(task_id=SEARCH_TASK_ID))
    return runner, assignment_service


def run(max_ticks: int = 150) -> tuple[SimulationState, list[StepOutcome], SimulationRunner]:
    runner, assignment_service = build()
    outcomes: list[StepOutcome] = []

    for _ in range(max_ticks):
        state, outcome = runner.step()
        outcomes.append(outcome)

        # React to discovery: assign all robots to the rescue task.
        for task, _ in outcome.tasks_spawned:
            if task.id == RESCUE_POINT_ID:
                assignment_service.update([
                    Assignment(task_id=task.id, robot_id=robot_id)
                    for robot_id in ROBOT_IDS
                ])

        if RESCUE_POINT_ID in outcome.tasks_completed:
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
        for _ in range(150):
            state, outcome = runner.step()
            outcomes.append(outcome)

            for task, _ in outcome.tasks_spawned:
                if task.id == RESCUE_POINT_ID:
                    assignment_service.update([
                        Assignment(task_id=task.id, robot_id=robot_id)
                        for robot_id in ROBOT_IDS
                    ])

            terminal = os.get_terminal_size()
            frame = view.render(state, width=terminal.columns, height=terminal.lines)
            renderer.draw(frame)

            if RESCUE_POINT_ID in outcome.tasks_completed:
                time.sleep(0.5)
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

    print(runner.stop())
    print(f"Rescue point discovered at tick: {discovery_tick}")
    print(f"Final robot positions: {final_positions}")
    print(f"Distance to rescue point: { {rid: pos.manhattan(_RESCUE_POSITION) for rid, pos in final_positions.items()} }")
