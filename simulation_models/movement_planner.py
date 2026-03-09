"""
Movement Planner

Pure functions for planning robot movement each simulation tick.
No simulation state is held here — all inputs are explicit.
"""

from __future__ import annotations

from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.task import Task


def resolve_task_target_position(
    task: Task,
    robot_pos: Position,
    environment: Environment,
) -> Position | None:
    """Resolve a task's spatial constraint to a concrete target Position.

    Returns:
        The target Position, or None if the task has no spatial constraint
        or the referenced zone does not exist in the environment.
    """
    sc = task.spatial_constraint
    if sc is None:
        return None

    if isinstance(sc.target, Position):
        return sc.target

    # ZoneId — find nearest zone cell to the robot (Manhattan distance)
    zone = environment.get_zone(sc.target)
    if zone is None:
        return None

    return min(zone.cells, key=lambda cell: robot_pos.manhattan(cell))
