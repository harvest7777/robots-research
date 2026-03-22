"""
Environment panel: 2D grid visualization.

Returns one string per grid row with robots, obstacles, task targets,
work areas, rescue points, and zones overlaid.
"""

from __future__ import annotations

from simulation.domain import (
    TaskId, TaskStatus, Environment, MoveTask, MoveTaskState, SearchTask,
    SearchTaskState, WorkTask, )
from simulation.primitives import Position
from simulation.domain import SimulationState

from simulation_view.terminal.symbols import (
    ROBOT_SYMBOL,
    OBSTACLE_SYMBOL,
    TASK_AREA_SYMBOL,
    RESCUE_POINT_SYMBOL,
    MOVE_TASK_SYMBOL,
    EMPTY_SYMBOL,
    ZONE_SYMBOLS,
    task_id_symbol,
)


def render_environment(state: SimulationState) -> list[str]:
    """Return one string per grid row with all overlays applied."""
    env = state.environment

    robot_positions: dict[Position, object] = {}
    for rid, rs in state.robot_states.items():
        cell = Position(int(rs.position.x), int(rs.position.y))
        robot_positions[cell] = rid

    targets, areas = _compute_task_work_areas(state)
    rescue_found: set[object] = set()
    for ts in state.task_states.values():
        if isinstance(ts, SearchTaskState):
            rescue_found.update(ts.rescue_found)
    rescue_point_positions: set[Position] = {
        rp.position for rp in env.rescue_points.values()
        if rp.id not in rescue_found
    }
    move_task_positions: set[Position] = {
        ts.current_position
        for task in state.tasks.values()
        if isinstance(task, MoveTask)
        for ts in [state.task_states.get(task.id)]
        if isinstance(ts, MoveTaskState)
        and ts.status not in (TaskStatus.DONE, TaskStatus.FAILED)
    }

    rows: list[str] = []
    for y in range(env.height):
        row_chars: list[str] = []
        for x in range(env.width):
            pos = Position(x, y)
            if pos in robot_positions:
                symbol = ROBOT_SYMBOL
            elif pos in env.obstacles:
                symbol = OBSTACLE_SYMBOL
            elif pos in rescue_point_positions:
                symbol = RESCUE_POINT_SYMBOL
            elif pos in move_task_positions:
                symbol = MOVE_TASK_SYMBOL
            elif pos in targets:
                symbol = task_id_symbol(targets[pos])
            elif pos in areas:
                symbol = TASK_AREA_SYMBOL
            else:
                zone_sym = _zone_symbol_at(env, pos)
                symbol = zone_sym if zone_sym else EMPTY_SYMBOL
            row_chars.append(symbol)
        rows.append(" ".join(row_chars))

    return rows


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _compute_task_work_areas(
    state: SimulationState,
) -> tuple[dict[Position, TaskId], dict[Position, TaskId]]:
    """Compute target cells and work-area cells for active tasks.

    Returns:
        targets: exact task target positions → task_id
        areas:   work-radius or zone cells → task_id (target takes priority)
    """
    targets: dict[Position, TaskId] = {}
    areas: dict[Position, TaskId] = {}
    env = state.environment

    for task in state.tasks.values():
        if isinstance(task, SearchTask):
            continue  # search tasks roam freely; no fixed spatial target
        if not isinstance(task, WorkTask):
            continue
        ts = state.task_states.get(task.id)
        if ts is not None and ts.status in (TaskStatus.DONE, TaskStatus.FAILED):
            continue
        sc = task.spatial_constraint
        if sc is None:
            continue
        if isinstance(sc.target, Position):
            targets.setdefault(sc.target, task.id)
            if sc.max_distance > 0:
                for dy in range(-sc.max_distance, sc.max_distance + 1):
                    for dx in range(-sc.max_distance, sc.max_distance + 1):
                        if abs(dx) + abs(dy) <= sc.max_distance:
                            p = Position(sc.target.x + dx, sc.target.y + dy)
                            if p != sc.target and 0 <= p.x < env.width and 0 <= p.y < env.height:
                                areas.setdefault(p, task.id)
        else:
            zone = env.get_zone(sc.target)
            if zone is not None:
                for p in zone.cells:
                    areas.setdefault(p, task.id)

    return targets, areas


def _zone_symbol_at(env: Environment, pos: Position) -> str | None:
    """Return the zone display symbol for pos, or None if not in any zone."""
    for zone in env._zones.values():
        if zone.contains(pos):
            return ZONE_SYMBOLS.get(zone.zone_type, "?")
    return None
