"""
Display constants and pure symbol-derivation functions.

No domain logic, no imports from the engine. Pure functions that map
task/state data to display strings.
"""

from __future__ import annotations

from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId, TaskStatus
from simulation.domain.task import Task, TaskType
from simulation.domain.search_task import SearchTask
from simulation.domain.task_state import TaskState
from simulation.primitives.zone import ZoneType

# ---------------------------------------------------------------------------
# Grid display constants
# ---------------------------------------------------------------------------

ROBOT_SYMBOL = "R"
OBSTACLE_SYMBOL = "#"
TASK_AREA_SYMBOL = "+"
RESCUE_POINT_SYMBOL = "^"
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

TASK_TYPE_LABELS: dict[TaskType, str] = {
    TaskType.ROUTINE_INSPECTION: "RI",
    TaskType.ANOMALY_INVESTIGATION: "AI",
    TaskType.PREVENTIVE_MAINTENANCE: "PM",
    TaskType.EMERGENCY_RESPONSE: "ER",
    TaskType.PICKUP: "PU",
    TaskType.IDLE: "--",
    TaskType.RESCUE: "RS",
}

TASK_TYPE_FULL_NAMES: dict[TaskType, str] = {
    TaskType.ROUTINE_INSPECTION: "Routine Inspection",
    TaskType.ANOMALY_INVESTIGATION: "Anomaly Investigation",
    TaskType.PREVENTIVE_MAINTENANCE: "Preventive Maintenance",
    TaskType.EMERGENCY_RESPONSE: "Emergency Response",
    TaskType.PICKUP: "Pickup",
    TaskType.IDLE: "Idle",
    TaskType.RESCUE: "Rescue",
}

# ---------------------------------------------------------------------------
# Pure symbol-derivation functions
# ---------------------------------------------------------------------------


def task_label(task: BaseTask) -> str:
    """Return a short 2-char label for a task (e.g. "SR", "RI")."""
    if isinstance(task, SearchTask):
        return "SR"
    assert isinstance(task, Task)
    return TASK_TYPE_LABELS.get(task.type, "??")


def task_full_name(task: BaseTask) -> str:
    """Return a human-readable name for a task."""
    if isinstance(task, SearchTask):
        return "Search"
    assert isinstance(task, Task)
    return TASK_TYPE_FULL_NAMES.get(task.type, "Unknown")


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
