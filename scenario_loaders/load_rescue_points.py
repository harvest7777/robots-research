from __future__ import annotations

from typing import Any

from simulation_models.position import Position
from simulation_models.rescue_point import RescuePoint, RescuePointId
from simulation_models.task import TaskId


def load_rescue_points(raw: list[dict[str, Any]]) -> list[RescuePoint]:
    """Load a list of RescuePoints from raw config data.

    Args:
        raw: List of rescue_point dictionaries, each with required keys:
            id: Non-negative integer identifier.
            name: Human-readable string label.
            position: [x, y] integer coordinates.
            rescue_task_id: Integer ID of the RESCUE task to trigger.

    Returns:
        List of configured RescuePoint instances.

    Raises:
        KeyError: If required keys are missing.
        ValueError: If values are invalid or IDs are duplicated.
    """
    rescue_points: list[RescuePoint] = []
    seen_ids: set[int] = set()

    for i, rp_raw in enumerate(raw):
        for key in ("id", "name", "position", "rescue_task_id"):
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

        rescue_task_id = rp_raw["rescue_task_id"]
        if not isinstance(rescue_task_id, int) or rescue_task_id < 0:
            raise ValueError(
                f"rescue_point {rp_id}: rescue_task_id must be a non-negative integer, "
                f"got: {rescue_task_id!r}"
            )

        rescue_points.append(RescuePoint(
            id=RescuePointId(rp_id),
            position=Position(x, y),
            name=name,
            rescue_task_id=TaskId(rescue_task_id),
        ))

    return rescue_points
