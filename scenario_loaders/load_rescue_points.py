from __future__ import annotations

from typing import Any

from simulation.primitives.position import Position
from simulation.domain.rescue_point import RescuePoint, RescuePointId
from simulation.domain.task import TaskId, SpatialConstraint
from simulation.primitives.time import Time


def load_rescue_points(raw: list[dict[str, Any]]) -> list[RescuePoint]:
    """Load a list of RescuePoints from raw config data.

    Args:
        raw: List of rescue_point dictionaries, each with required keys:
            id:                 Non-negative integer identifier. Also serves as the
                                task ID when the rescue point becomes an active task.
            name:               Human-readable string label.
            position:           [x, y] integer coordinates.
            required_work_time: Ticks of work to complete the rescue (default: 40).
            min_robots_needed:  Minimum robots to assign (default: 1).
            priority:           Scheduling priority (default: 10).

        Note: rescue_task_id is no longer a separate field. The rescue point's
        own id is used as the task id when it becomes active on discovery.
        If rescue_task_id is present in the raw data it is silently ignored.

    Returns:
        List of configured RescuePoint instances.

    Raises:
        KeyError: If required keys are missing.
        ValueError: If values are invalid or IDs are duplicated.
    """
    rescue_points: list[RescuePoint] = []
    seen_ids: set[int] = set()

    for i, rp_raw in enumerate(raw):
        for key in ("id", "name", "position"):
            if key not in rp_raw:
                raise KeyError(f"rescue_point at index {i} missing required key: '{key}'")

        rp_id = rp_raw["id"]
        if not isinstance(rp_id, int) or rp_id < 0:
            raise ValueError(
                f"rescue_point id must be a non-negative integer, got: {rp_id!r}"
            )
        if rp_id in seen_ids:
            raise ValueError(f"duplicate rescue_point id: {rp_id}")
        seen_ids.add(rp_id)

        name = rp_raw["name"]
        if not isinstance(name, str):
            raise ValueError(f"rescue_point {rp_id}: name must be a string, got: {name!r}")

        position_raw = rp_raw["position"]
        if not isinstance(position_raw, list) or len(position_raw) != 2:
            raise ValueError(
                f"rescue_point {rp_id}: position must be [x, y], got: {position_raw!r}"
            )
        x, y = position_raw
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError(
                f"rescue_point {rp_id}: position coordinates must be integers, "
                f"got: {position_raw!r}"
            )

        required_work_time = rp_raw.get("required_work_time", 40)
        min_robots_needed = rp_raw.get("min_robots_needed", 1)
        priority = rp_raw.get("priority", 10)

        rescue_points.append(RescuePoint(
            id=RescuePointId(rp_id),
            priority=priority,
            spatial_constraint=SpatialConstraint(target=Position(x, y), max_distance=0),
            required_work_time=Time(required_work_time),
            min_robots_needed=min_robots_needed,
            name=name,
        ))

    return rescue_points
