"""
Scenario: mega_multi_rescue

A larger, obstacle-dense environment with multiple concurrent objectives:

- 3 independent search-and-discover events (3 rescue points / casualties)
- 3 independent carry/extract MoveTasks that run in parallel once discovered
- 2 additional "other" WorkTasks (inspection/maintenance-style work) that run
  concurrently to stress scheduling and pathfinding contention
- Multiple Zones (restricted / inspection / charging / loading) for richer UI

This is intentionally "busy": many robots, many obstacles, multiple districts.
The scenario loop uses the same event-driven pattern as the smaller
search-and-rescue scenarios: discovery (outcome.tasks_spawned) triggers dynamic
reassignment to the corresponding MoveTask.

Expected outcome:
- All 3 MoveTasks complete before max_ticks.
- The two auxiliary WorkTasks also complete (unless you intentionally reassign
  all robots away from them).
"""

from __future__ import annotations

from collections.abc import Iterable

from simulation.algorithms import astar_pathfind
from simulation.domain import (
    Environment,
    MoveTask,
    MoveTaskState,
    RescuePoint,
    Robot,
    RobotId,
    RobotState,
    SearchTask,
    SpatialConstraint,
    TaskId,
    TaskState,
    WorkTask,
)
from simulation.domain.search_task import SearchTaskState
from simulation.engine_rewrite import Assignment, SimulationRunner, SimulationState, StepOutcome
from simulation.engine_rewrite.services import (
    BaseAssignmentService,
    InMemoryAssignmentService,
    InMemorySimulationStore,
)
from simulation.primitives import Capability, Position, Time, Zone, ZoneId, ZoneType


# ---------------------------------------------------------------------------
# IDs
# ---------------------------------------------------------------------------

SEARCH_TASK_ID = TaskId(1)

RESCUE_POINT_A_ID = TaskId(10)
RESCUE_POINT_B_ID = TaskId(11)
RESCUE_POINT_C_ID = TaskId(12)

MOVE_TASK_A_ID = TaskId(20)
MOVE_TASK_B_ID = TaskId(21)
MOVE_TASK_C_ID = TaskId(22)

AUX_WORK_1_ID = TaskId(30)
AUX_WORK_2_ID = TaskId(31)

ROBOT_IDS = [RobotId(i) for i in range(1, 13)]  # 12 robots


# ---------------------------------------------------------------------------
# Map layout
# ---------------------------------------------------------------------------

_WIDTH = 40
_HEIGHT = 24

# Casualties ("discoverable points") placed in three different districts.
_CASUALTY_A_POS = Position(6, 6)
_CASUALTY_B_POS = Position(33, 7)
_CASUALTY_C_POS = Position(21, 18)

# Extraction/safe zones.
_EXTRACTION_A_POS = Position(2, 2)
_EXTRACTION_B_POS = Position(37, 2)
_EXTRACTION_C_POS = Position(29, 21)

# Two auxiliary work targets.
_AUX_WORK_1_POS = Position(5, 20)
_AUX_WORK_2_POS = Position(18, 3)


def _rect(x0: int, y0: int, x1: int, y1: int) -> list[Position]:
    """Inclusive rectangle of positions."""
    return [Position(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]


def _ring(cx: int, cy: int, r: int) -> list[Position]:
    """A hollow square ring around (cx, cy) at manhattan-ish radius r."""
    out: list[Position] = []
    x0, y0, x1, y1 = cx - r, cy - r, cx + r, cy + r
    for x in range(x0, x1 + 1):
        out.append(Position(x, y0))
        out.append(Position(x, y1))
    for y in range(y0 + 1, y1):
        out.append(Position(x0, y))
        out.append(Position(x1, y))
    # de-dupe while preserving determinism
    seen: set[Position] = set()
    uniq: list[Position] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def _build_obstacles() -> list[Position]:
    """
    Dense-but-navigable obstacle field split into 3 districts with corridors.

    Design goals:
    - Force detours and contention without deadlocking the MoveTasks
    - Keep at least 2 distinct corridors between districts
    """
    obstacles: list[Position] = []

    # District walls (partial) to create "rooms" and corridors
    obstacles += _rect(0, 9, 14, 9)     # horizontal wall left
    obstacles += _rect(25, 10, 39, 10)  # horizontal wall right

    # Gaps (corridors) carved out by *not* placing obstacles at:
    # - around x=7..8, y=9
    # - around x=31..32, y=10
    # We'll explicitly remove those after building.

    # Central "rubble city" (broken blocks) to stress pathfinding
    obstacles += _rect(16, 6, 18, 8)
    obstacles += _rect(20, 6, 22, 7)
    obstacles += _rect(16, 10, 17, 12)
    obstacles += _rect(19, 11, 22, 12)
    obstacles += _rect(15, 14, 17, 16)
    obstacles += _rect(19, 14, 20, 16)

    # Casualty neighborhood clutter (clusters) to force approach angle variation
    # without fully enclosing the carry object (formations must be able to exit).
    # Keep A relatively open so the carry can "get moving" quickly.
    obstacles += [
        Position(_CASUALTY_A_POS.x + 1, _CASUALTY_A_POS.y - 2),
        Position(_CASUALTY_A_POS.x + 2, _CASUALTY_A_POS.y - 2),
        Position(_CASUALTY_A_POS.x + 2, _CASUALTY_A_POS.y - 1),
    ]
    obstacles += _rect(_CASUALTY_B_POS.x - 2, _CASUALTY_B_POS.y - 1, _CASUALTY_B_POS.x - 2, _CASUALTY_B_POS.y + 2)
    obstacles += _rect(_CASUALTY_B_POS.x + 2, _CASUALTY_B_POS.y - 2, _CASUALTY_B_POS.x + 2, _CASUALTY_B_POS.y + 1)
    obstacles += _rect(_CASUALTY_C_POS.x - 3, _CASUALTY_C_POS.y - 1, _CASUALTY_C_POS.x - 1, _CASUALTY_C_POS.y - 1)
    obstacles += _rect(_CASUALTY_C_POS.x + 1, _CASUALTY_C_POS.y + 1, _CASUALTY_C_POS.x + 3, _CASUALTY_C_POS.y + 1)

    # Southern clutter (blocks), but keep broad connectivity.
    obstacles += _rect(3, 16, 8, 17)
    obstacles += _rect(14, 17, 17, 19)
    obstacles += _rect(23, 16, 25, 18)
    obstacles += _rect(31, 18, 34, 19)

    # Remove corridor gaps in the district walls
    blocked = set(obstacles)
    for p in [Position(7, 9), Position(8, 9), Position(31, 10), Position(32, 10)]:
        blocked.discard(p)

    # Ensure we never block the exact task targets/extractions
    for p in [
        _CASUALTY_A_POS,
        _CASUALTY_B_POS,
        _CASUALTY_C_POS,
        _EXTRACTION_A_POS,
        _EXTRACTION_B_POS,
        _EXTRACTION_C_POS,
        _AUX_WORK_1_POS,
        _AUX_WORK_2_POS,
    ]:
        blocked.discard(p)

    return sorted(blocked, key=lambda pos: (pos.y, pos.x))


_OBSTACLES = _build_obstacles()


_ROBOT_STARTS: dict[RobotId, Position] = {
    # 4 searchers placed near different corridors / districts
    # Start *adjacent* so proximity discovery triggers immediately.
    RobotId(1): Position(6, 7),    # adjacent to casualty A
    RobotId(2): Position(33, 8),   # adjacent to casualty B
    RobotId(3): Position(21, 19),  # adjacent to casualty C
    RobotId(4): Position(19, 9),   # central roamer
    # carriers / workers distributed widely to create contention
    RobotId(5): Position(1, 22),
    RobotId(6): Position(10, 22),
    RobotId(7): Position(38, 22),
    RobotId(8): Position(30, 21),
    RobotId(9): Position(5, 6),   # near casualty A so team A can form quickly
    RobotId(10): Position(37, 12),
    RobotId(11): Position(18, 1),
    RobotId(12): Position(22, 1),
}


def _zone_cells(positions: Iterable[Position]) -> frozenset[Position]:
    return frozenset(positions)


def build(
    assignment_service: BaseAssignmentService | None = None,
) -> tuple[SimulationRunner, BaseAssignmentService]:
    env = Environment(width=_WIDTH, height=_HEIGHT)
    for pos in _OBSTACLES:
        # Bounds guards (ring builder can generate out-of-bounds at edges)
        if 0 <= pos.x < _WIDTH and 0 <= pos.y < _HEIGHT:
            env.add_obstacle(pos)

    # Zones (non-overlapping by construction)
    env.add_zone(
        Zone.from_positions(
            id=ZoneId(1),
            zone_type=ZoneType.RESTRICTED,
            positions=_zone_cells(_rect(0, 0, 4, 4)),
        )
    )
    env.add_zone(
        Zone.from_positions(
            id=ZoneId(2),
            zone_type=ZoneType.INSPECTION,
            positions=_zone_cells(_rect(15, 0, 23, 4)),
        )
    )
    env.add_zone(
        Zone.from_positions(
            id=ZoneId(3),
            zone_type=ZoneType.CHARGING,
            positions=_zone_cells(_rect(35, 18, 39, 23)),
        )
    )
    env.add_zone(
        Zone.from_positions(
            id=ZoneId(4),
            zone_type=ZoneType.LOADING,
            positions=_zone_cells(_rect(0, 18, 6, 23)),
        )
    )

    # Rescue points: discovery spawns the actual MoveTask + its state.
    def _rescue_point(
        rp_id: TaskId,
        name: str,
        casualty_pos: Position,
        move_task_id: TaskId,
        extraction_pos: Position,
        min_robots_required: int,
    ) -> RescuePoint:
        move_task = MoveTask(
            id=move_task_id,
            priority=9,
            destination=extraction_pos,
            min_robots_required=min_robots_required,
            min_distance=1,
            required_capabilities=frozenset({Capability.VISION}),
        )
        return RescuePoint(
            id=rp_id,
            name=name,
            spatial_constraint=SpatialConstraint(target=casualty_pos, max_distance=1),
            task=move_task,
            initial_task_state=MoveTaskState(task_id=move_task_id, current_position=casualty_pos),
        )

    env.add_rescue_point(
        _rescue_point(
            rp_id=RESCUE_POINT_A_ID,
            name="Casualty A",
            casualty_pos=_CASUALTY_A_POS,
            move_task_id=MOVE_TASK_A_ID,
            extraction_pos=_EXTRACTION_A_POS,
            min_robots_required=2,
        )
    )
    env.add_rescue_point(
        _rescue_point(
            rp_id=RESCUE_POINT_B_ID,
            name="Casualty B",
            casualty_pos=_CASUALTY_B_POS,
            move_task_id=MOVE_TASK_B_ID,
            extraction_pos=_EXTRACTION_B_POS,
            min_robots_required=2,
        )
    )
    env.add_rescue_point(
        _rescue_point(
            rp_id=RESCUE_POINT_C_ID,
            name="Casualty C",
            casualty_pos=_CASUALTY_C_POS,
            move_task_id=MOVE_TASK_C_ID,
            extraction_pos=_EXTRACTION_C_POS,
            min_robots_required=2,
        )
    )

    search = SearchTask(
        id=SEARCH_TASK_ID,
        priority=5,
        required_capabilities=frozenset({Capability.VISION}),
    )

    # Auxiliary tasks ("other tasks")
    aux_1 = WorkTask(
        id=AUX_WORK_1_ID,
        priority=4,
        required_work_time=Time(60),
        spatial_constraint=SpatialConstraint(target=_AUX_WORK_1_POS, max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )
    aux_2 = WorkTask(
        id=AUX_WORK_2_ID,
        priority=4,
        required_work_time=Time(40),
        spatial_constraint=SpatialConstraint(target=_AUX_WORK_2_POS, max_distance=0),
        required_capabilities=frozenset({Capability.VISION}),
    )

    store = InMemorySimulationStore()

    # Initial staffing:
    # - 4 robots search
    # - 4 robots start on aux work tasks (2 each)
    # - remaining robots idle until discovery reassigns them to MoveTasks
    initial_assignments = [
        Assignment(task_id=SEARCH_TASK_ID, robot_id=RobotId(1)),
        Assignment(task_id=SEARCH_TASK_ID, robot_id=RobotId(2)),
        Assignment(task_id=SEARCH_TASK_ID, robot_id=RobotId(3)),
        Assignment(task_id=SEARCH_TASK_ID, robot_id=RobotId(4)),
        Assignment(task_id=AUX_WORK_1_ID, robot_id=RobotId(5)),
        Assignment(task_id=AUX_WORK_1_ID, robot_id=RobotId(6)),
        Assignment(task_id=AUX_WORK_2_ID, robot_id=RobotId(11)),
        Assignment(task_id=AUX_WORK_2_ID, robot_id=RobotId(12)),
    ]

    if assignment_service is None:
        assignment_service = InMemoryAssignmentService(assignments=initial_assignments)
    else:
        assignment_service.update(initial_assignments)

    runner = SimulationRunner(
        environment=env,
        store=store,
        assignment_service=assignment_service,
        pathfinding=astar_pathfind,
    )

    for robot_id in ROBOT_IDS:
        store.add_robot(
            Robot(id=robot_id, capabilities=frozenset({Capability.VISION})),
            RobotState(robot_id=robot_id, position=_ROBOT_STARTS[robot_id]),
        )

    store.add_task(search, SearchTaskState(task_id=SEARCH_TASK_ID))
    store.add_task(aux_1, TaskState(task_id=AUX_WORK_1_ID))
    store.add_task(aux_2, TaskState(task_id=AUX_WORK_2_ID))

    return runner, assignment_service


def _handle_discoveries(outcome: StepOutcome, assignment_service: BaseAssignmentService) -> None:
    found = set(outcome.rescue_points_found)

    if RESCUE_POINT_A_ID in found:
        assignment_service.update(
            [
                Assignment(task_id=MOVE_TASK_A_ID, robot_id=RobotId(1)),
                Assignment(task_id=MOVE_TASK_A_ID, robot_id=RobotId(9)),
            ]
        )
    if RESCUE_POINT_B_ID in found:
        assignment_service.update(
            [
                Assignment(task_id=MOVE_TASK_B_ID, robot_id=RobotId(2)),
                Assignment(task_id=MOVE_TASK_B_ID, robot_id=RobotId(10)),
            ]
        )
    if RESCUE_POINT_C_ID in found:
        assignment_service.update(
            [
                Assignment(task_id=MOVE_TASK_C_ID, robot_id=RobotId(3)),
                Assignment(task_id=MOVE_TASK_C_ID, robot_id=RobotId(6)),
            ]
        )


def run(max_ticks: int = 900) -> tuple[SimulationState, list[StepOutcome], SimulationRunner]:
    runner, assignment_service = build()
    outcomes: list[StepOutcome] = []

    completed: set[TaskId] = set()
    goal = {MOVE_TASK_A_ID, MOVE_TASK_B_ID, MOVE_TASK_C_ID, AUX_WORK_1_ID, AUX_WORK_2_ID}

    for _ in range(max_ticks):
        state, outcome = runner.step()
        outcomes.append(outcome)
        completed.update(outcome.tasks_completed)
        _handle_discoveries(outcome, assignment_service)

        if completed >= goal:
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
    completed: set[TaskId] = set()
    goal = {MOVE_TASK_A_ID, MOVE_TASK_B_ID, MOVE_TASK_C_ID, AUX_WORK_1_ID, AUX_WORK_2_ID}

    try:
        for _ in range(900):
            state, outcome = runner.step()
            outcomes.append(outcome)
            completed.update(outcome.tasks_completed)
            _handle_discoveries(outcome, assignment_service)

            terminal = os.get_terminal_size()
            frame = view.render(state, width=terminal.columns, height=terminal.lines)
            renderer.draw(frame)

            if completed >= goal:
                time.sleep(1.0)
                break

            time.sleep(0.1)
    finally:
        renderer.cleanup()

    print(runner.stop())
