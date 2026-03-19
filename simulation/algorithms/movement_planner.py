"""
Movement Planner

Pure functions for planning robot movement each simulation tick.
No simulation state is held here — all inputs are explicit.
"""

from __future__ import annotations

from collections.abc import Callable

from simulation.domain.environment import Environment
from simulation.primitives.position import Position
from simulation.domain.robot_state import RobotId


PathfindingAlgorithm = Callable[[Environment, Position, Position], Position | None]
GoalResolver = Callable[[RobotId, "RobotState"], Position | None]


def resolve_collisions(
    planned_moves: dict[RobotId, Position | None],
    current_positions: dict[RobotId, Position],
) -> dict[RobotId, Position | None]:
    """Resolve movement conflicts so no two robots occupy the same cell.

    Iterative algorithm — repeat until stable:
      1. Compute every robot's intended end position (planned or current).
      2. For each end position:
         - If a staying robot is there, cancel every mover heading there.
         - If multiple movers target the same empty cell, keep the
           lowest robot_id, cancel the rest.
      3. Each cancellation turns a mover into a stayer, which can expose
         new conflicts in the next pass.

    Convergence: every iteration cancels ≥1 move, so the loop terminates
    in at most O(n) passes.

    Returns a new dict; does not mutate the input.
    """
    resolved = dict(planned_moves)

    changed = True
    while changed:
        changed = False

        end_pos: dict[Position, list[RobotId]] = {}
        for rid in resolved:
            pos = resolved[rid] if resolved[rid] is not None else current_positions[rid]
            end_pos.setdefault(pos, []).append(rid)

        for pos, rids in end_pos.items():
            stayers = [rid for rid in rids if resolved[rid] is None]
            movers  = [rid for rid in rids if resolved[rid] is not None]

            if stayers and movers:
                for rid in movers:
                    resolved[rid] = None
                changed = True
            elif len(movers) > 1:
                for rid in sorted(movers)[1:]:
                    resolved[rid] = None
                changed = True

    return resolved
