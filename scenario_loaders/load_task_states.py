from __future__ import annotations

from typing import Any

from simulation.domain.task import TaskId
from simulation.domain.task_state import TaskState, TaskStatus
from simulation.primitives.time import Time


def load_task_states(raw: list[dict[str, Any]]) -> list[TaskState]:
    """Load a list of TaskStates from raw config data.

    Args:
        raw: List of task_state dictionaries, each with required keys:
            task_id: Integer identifier matching a Task.

            Optional keys:
            status: One of "unassigned", "in_progress", "done", "failed".
                    Defaults to "unassigned".
            work_done: Integer tick count of work completed. Defaults to 0.
            started_at: Integer tick count when task started.
            completed_at: Integer tick count when task completed.

    Returns:
        List of configured TaskState instances.

    Raises:
        KeyError: If required keys are missing.
        ValueError: If values are invalid.
    """
    task_states: list[TaskState] = []
    seen_ids: set[int] = set()

    for i, state_raw in enumerate(raw):
        if "task_id" not in state_raw:
            raise KeyError(f"task_state at index {i} missing required key: 'task_id'")

        task_id = state_raw["task_id"]

        if not isinstance(task_id, int) or task_id < 0:
            raise ValueError(
                f"task_state task_id must be a non-negative integer, got: {task_id!r}"
            )

        if task_id in seen_ids:
            raise ValueError(f"duplicate task_state for task_id: {task_id}")
        seen_ids.add(task_id)

        # Parse optional status
        status = TaskStatus.UNASSIGNED
        if "status" in state_raw:
            status_str = state_raw["status"]
            try:
                status = TaskStatus(status_str)
            except ValueError:
                valid_statuses = [s.value for s in TaskStatus]
                raise ValueError(
                    f"task_state {task_id}: invalid status: {status_str!r}, "
                    f"must be one of {valid_statuses}"
                )

        # Parse optional work_done
        work_done = Time(0)
        if "work_done" in state_raw:
            work_done_raw = state_raw["work_done"]
            if not isinstance(work_done_raw, int) or work_done_raw < 0:
                raise ValueError(
                    f"task_state {task_id}: work_done must be a non-negative integer, "
                    f"got: {work_done_raw!r}"
                )
            work_done = Time(work_done_raw)

        # Parse optional started_at
        started_at: Time | None = None
        if "started_at" in state_raw:
            started_at_raw = state_raw["started_at"]
            if not isinstance(started_at_raw, int) or started_at_raw < 0:
                raise ValueError(
                    f"task_state {task_id}: started_at must be a non-negative integer, "
                    f"got: {started_at_raw!r}"
                )
            started_at = Time(started_at_raw)

        # Parse optional completed_at
        completed_at: Time | None = None
        if "completed_at" in state_raw:
            completed_at_raw = state_raw["completed_at"]
            if not isinstance(completed_at_raw, int) or completed_at_raw < 0:
                raise ValueError(
                    f"task_state {task_id}: completed_at must be a non-negative integer, "
                    f"got: {completed_at_raw!r}"
                )
            completed_at = Time(completed_at_raw)

        task_state = TaskState(
            task_id=TaskId(task_id),
            status=status,
            work_done=work_done,
            started_at=started_at,
            completed_at=completed_at,
        )
        task_states.append(task_state)

    return task_states
