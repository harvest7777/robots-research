"""
StepOutcome and IgnoreReason (new design)

StepOutcome is the complete description of what happened in one simulation tick.
It is produced by classify_step (Observer) and consumed by:
  - apply_outcome  (state mutation)
  - SimulationRunner (registry updates)
  - listeners       (MetricService, Assigner, etc.)

Rules:
- Every positive outcome is in moved or worked.
- Every assignment that produced no progress this tick is in assignments_ignored.
- Idle robots are derived (not in moved, not in worked) — not stored explicitly.
- Battery drain is derived in apply_outcome from moved/worked/idle classification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId
from simulation.domain.robot_state import RobotId
from simulation.primitives.position import Position

from simulation.domain import Assignment


class IgnoreReason(Enum):
    NO_BATTERY       = "no_battery"        # robot has 0 battery — cannot act
    WRONG_CAPABILITY = "wrong_capability"  # robot lacks required capabilities
    TASK_TERMINAL    = "task_terminal"     # task is already done or failed
    NO_PATH          = "no_path"           # pathfinding could not reach task location


@dataclass
class StepOutcome:
    moved:               list[tuple[RobotId, Position]]          = field(default_factory=list)
    worked:              list[tuple[RobotId, TaskId]]            = field(default_factory=list)
    tasks_completed:     list[TaskId]                            = field(default_factory=list)
    tasks_spawned:       list[tuple[BaseTask, BaseTaskState]]    = field(default_factory=list)
    assignments_ignored: list[tuple[Assignment, IgnoreReason]]   = field(default_factory=list)
    rescue_points_found: list[TaskId]                            = field(default_factory=list)
    # rescue_points_found: needed so apply_outcome can update SearchTaskState.rescue_found
    # without re-deriving it (which would be business logic leaking into apply_outcome).
    waypoints:           dict[RobotId, Position]                 = field(default_factory=dict)
    # waypoints: proposed next waypoint per robot this tick, written by Observer and
    # applied to RobotState.current_waypoint by apply_outcome. Keeps classify_step pure.
    tasks_moved:         list[tuple[TaskId, Position]]           = field(default_factory=list)
    # tasks_moved: new position for each MoveTask that advanced this tick.
    # Written by Observer; applied to MoveTaskState.current_position by apply_outcome.

    # -------------------------------------------------------------------------
    # Training metadata — enriched signals for per-step model training
    # -------------------------------------------------------------------------
    robots_stuck:        list[RobotId]                           = field(default_factory=list)
    # robots_stuck: robots that had a valid intended move this tick but were held
    # in place by collision resolution. Indicates congestion or pathfinding
    # contention at the robot's position. Detectable by comparing intended_moves
    # (pathfinder output) against resolve_collisions output.

    collision_diversions: list[tuple[RobotId, Position, Position]] = field(default_factory=list)
    # collision_diversions: (robot_id, intended_position, actual_position) for
    # robots that moved but to a different cell than pathfinding planned.
    # Indicates the robot was re-routed to avoid a collision — weaker than stuck
    # but still a signal of local congestion near that assignment area.

    task_distances:      dict[RobotId, int]                      = field(default_factory=dict)
    # task_distances: manhattan distance from each robot's effective position this
    # tick to its assignment waypoint. 0 means the robot is at (or working on)
    # its target; large persistent values signal poor assignment locality or a
    # robot repeatedly assigned to a far region of the warehouse.
