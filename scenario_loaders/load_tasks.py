from __future__ import annotations

from typing import Any

from simulation_models.capability import Capability
from simulation_models.position import Position
from simulation_models.task import SpatialConstraint, Task, TaskId, TaskType
from simulation_models.time import Time
from simulation_models.zone import ZoneId


def load_tasks(raw: list[dict[str, Any]]) -> list[Task]:
    """Load a list of Tasks from raw config data.

    Args:
        raw: List of task dictionaries, each with required keys:
            id: Unique integer identifier for the task.
            type: One of "routine_inspection", "anomaly_investigation",
                  "preventive_maintenance", "emergency_response", "pickup".
            priority: Integer priority (higher = more important).
            required_work_time: Integer tick count for work duration.

            Optional keys:
            spatial_constraint: Object with "target" ([x, y] or zone_id int) and
                                optional "max_distance" (default 0).
            required_capabilities: Array of capability strings.
            dependencies: Array of task_id integers this task depends on.
            deadline: Integer tick count for deadline.

    Returns:
        List of configured Task instances.

    Raises:
        KeyError: If required keys are missing.
        ValueError: If values are invalid.
    """
    tasks: list[Task] = []
    seen_ids: set[int] = set()

    for i, task_raw in enumerate(raw):
        if "id" not in task_raw:
            raise KeyError(f"task at index {i} missing required key: 'id'")
        if "type" not in task_raw:
            raise KeyError(f"task at index {i} missing required key: 'type'")
        if "priority" not in task_raw:
            raise KeyError(f"task at index {i} missing required key: 'priority'")
        if "required_work_time" not in task_raw:
            raise KeyError(f"task at index {i} missing required key: 'required_work_time'")

        task_id = task_raw["id"]
        task_type_str = task_raw["type"]
        priority = task_raw["priority"]
        required_work_time = task_raw["required_work_time"]

        if not isinstance(task_id, int) or task_id < 0:
            raise ValueError(f"task id must be a non-negative integer, got: {task_id!r}")

        if task_id in seen_ids:
            raise ValueError(f"duplicate task id: {task_id}")
        seen_ids.add(task_id)

        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            valid_types = [t.value for t in TaskType]
            raise ValueError(
                f"invalid task type: {task_type_str!r}, must be one of {valid_types}"
            )

        if not isinstance(priority, int):
            raise ValueError(f"task {task_id}: priority must be an integer, got: {priority!r}")

        if not isinstance(required_work_time, int) or required_work_time < 0:
            raise ValueError(
                f"task {task_id}: required_work_time must be a non-negative integer, "
                f"got: {required_work_time!r}"
            )

        # Parse optional spatial_constraint
        spatial_constraint: SpatialConstraint | None = None
        if "spatial_constraint" in task_raw:
            spatial_constraint = _parse_spatial_constraint(task_id, task_raw["spatial_constraint"])

        # Parse optional required_capabilities
        required_capabilities: frozenset[Capability] = frozenset()
        if "required_capabilities" in task_raw:
            caps_raw = task_raw["required_capabilities"]
            if not isinstance(caps_raw, list):
                raise ValueError(f"task {task_id}: required_capabilities must be a list")
            caps: list[Capability] = []
            for cap_str in caps_raw:
                try:
                    caps.append(Capability(cap_str))
                except ValueError:
                    valid_caps = [c.value for c in Capability]
                    raise ValueError(
                        f"task {task_id}: invalid capability: {cap_str!r}, "
                        f"must be one of {valid_caps}"
                    )
            required_capabilities = frozenset(caps)

        # Parse optional dependencies
        dependencies: frozenset[TaskId] = frozenset()
        if "dependencies" in task_raw:
            deps_raw = task_raw["dependencies"]
            if not isinstance(deps_raw, list):
                raise ValueError(f"task {task_id}: dependencies must be a list")
            deps: list[TaskId] = []
            for dep_id in deps_raw:
                if not isinstance(dep_id, int) or dep_id < 0:
                    raise ValueError(
                        f"task {task_id}: dependency must be a non-negative integer, "
                        f"got: {dep_id!r}"
                    )
                deps.append(TaskId(dep_id))
            dependencies = frozenset(deps)

        # Parse optional deadline
        deadline: Time | None = None
        if "deadline" in task_raw:
            deadline_raw = task_raw["deadline"]
            if not isinstance(deadline_raw, int) or deadline_raw < 0:
                raise ValueError(
                    f"task {task_id}: deadline must be a non-negative integer, "
                    f"got: {deadline_raw!r}"
                )
            deadline = Time(deadline_raw)

        task = Task(
            id=TaskId(task_id),
            type=task_type,
            priority=priority,
            required_work_time=Time(required_work_time),
            spatial_constraint=spatial_constraint,
            required_capabilities=required_capabilities,
            dependencies=dependencies,
            deadline=deadline,
        )
        tasks.append(task)

    return tasks


def _parse_spatial_constraint(task_id: int, raw: dict[str, Any]) -> SpatialConstraint:
    """Parse a spatial constraint from raw config data."""
    if "target" not in raw:
        raise KeyError(f"task {task_id}: spatial_constraint missing required key: 'target'")

    target_raw = raw["target"]
    target: Position | ZoneId

    if isinstance(target_raw, list):
        if len(target_raw) != 2:
            raise ValueError(
                f"task {task_id}: spatial_constraint target must be [x, y], "
                f"got: {target_raw!r}"
            )
        x, y = target_raw
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError(
                f"task {task_id}: spatial_constraint target coordinates must be integers, "
                f"got: {target_raw!r}"
            )
        target = Position(x, y)
    elif isinstance(target_raw, int):
        target = ZoneId(target_raw)
    else:
        raise ValueError(
            f"task {task_id}: spatial_constraint target must be [x, y] or zone_id integer, "
            f"got: {target_raw!r}"
        )

    max_distance = raw.get("max_distance", 0)
    if not isinstance(max_distance, int) or max_distance < 0:
        raise ValueError(
            f"task {task_id}: spatial_constraint max_distance must be a non-negative integer, "
            f"got: {max_distance!r}"
        )

    return SpatialConstraint(target=target, max_distance=max_distance)
