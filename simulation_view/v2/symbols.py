"""
Display constants and pure symbol-derivation functions.

No domain logic, no imports from the engine. Pure functions that map
task/state data to display strings.
"""

from __future__ import annotations

from simulation.domain import BaseTask, BaseTaskState, TaskId, TaskStatus, MoveTask, RescuePoint, WorkTask, SearchTask, TaskState
from simulation.primitives import ZoneType

# ---------------------------------------------------------------------------
# Grid display constants
# ---------------------------------------------------------------------------

ROBOT_SYMBOL = "R"
OBSTACLE_SYMBOL = "#"
TASK_AREA_SYMBOL = "+"
RESCUE_POINT_SYMBOL = "^"
MOVE_TASK_SYMBOL = "□"
EMPTY_SYMBOL = "."

# ---------------------------------------------------------------------------
# Symbol dictionaries
# ---------------------------------------------------------------------------

ZONE_SYMBOLS: dict[ZoneType, str] = {
    ZoneType.INSPECTION: "I",
    ZoneType.MAINTENANCE: "M",
    ZoneType.LOADING: "L",
    ZoneType.RESTRICTED: "X",
    ZoneType.CHARGING: "C",
}

# ---------------------------------------------------------------------------
# Pure symbol-derivation functions
# ---------------------------------------------------------------------------


def task_label(task: BaseTask) -> str:
    """Return a short 2-char label for a task (e.g. "SR", "MV", "WK")."""
    if isinstance(task, SearchTask):
        return "SR"
    if isinstance(task, RescuePoint):
        return "RS"
    if isinstance(task, MoveTask):
        return "MV"
    assert isinstance(task, WorkTask)
    return "WK"


def task_full_name(task: BaseTask) -> str:
    """Return a human-readable name for a task."""
    if isinstance(task, SearchTask):
        return "Search"
    if isinstance(task, RescuePoint):
        return "Rescue"
    if isinstance(task, MoveTask):
        return "Move"
    assert isinstance(task, WorkTask)
    return "Work"


def task_status_symbol(state: BaseTaskState) -> str:
    """Return a Unicode symbol representing the task's current status.

    ●  DONE
    ✗  FAILED
    ◑  in progress (started_at is set)
    ○  not yet started
    """
    if state.status == TaskStatus.DONE:
        return "●"
    if state.status == TaskStatus.FAILED:
        return "✗"
    if isinstance(state, TaskState) and state.started_at is not None:
        return "◑"
    return "○"


def task_id_symbol(task_id: TaskId) -> str:
    """Return a single-char symbol for a task ID ("1"–"9", "*" for ≥10)."""
    return str(int(task_id)) if int(task_id) < 10 else "*"
