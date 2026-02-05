from __future__ import annotations

from typing import Any

from simulation_models.position import Position
from simulation_models.zone import Zone, ZoneId, ZoneType


def load_zones(raw: list[dict[str, Any]]) -> list[Zone]:
    """Load a list of Zones from raw config data.

    Args:
        raw: List of zone dictionaries, each with 'id', 'type', and 'positions' keys.
            id: Unique integer identifier for the zone.
            type: One of "inspection", "maintenance", "loading", "restricted", "charging".
            positions: Array of [x, y] positions that the zone covers.

    Returns:
        List of configured Zone instances.

    Raises:
        KeyError: If required keys are missing.
        ValueError: If values are invalid.
    """
    zones: list[Zone] = []
    seen_ids: set[int] = set()

    for i, zone_raw in enumerate(raw):
        if "id" not in zone_raw:
            raise KeyError(f"zone at index {i} missing required key: 'id'")
        if "type" not in zone_raw:
            raise KeyError(f"zone at index {i} missing required key: 'type'")
        if "positions" not in zone_raw:
            raise KeyError(f"zone at index {i} missing required key: 'positions'")

        zone_id = zone_raw["id"]
        zone_type_str = zone_raw["type"]
        positions_raw = zone_raw["positions"]

        if not isinstance(zone_id, int) or zone_id < 0:
            raise ValueError(f"zone id must be a non-negative integer, got: {zone_id!r}")

        if zone_id in seen_ids:
            raise ValueError(f"duplicate zone id: {zone_id}")
        seen_ids.add(zone_id)

        try:
            zone_type = ZoneType(zone_type_str)
        except ValueError:
            valid_types = [t.value for t in ZoneType]
            raise ValueError(
                f"invalid zone type: {zone_type_str!r}, must be one of {valid_types}"
            )

        if not isinstance(positions_raw, list) or len(positions_raw) == 0:
            raise ValueError(f"zone {zone_id} positions must be a non-empty list")

        positions: list[Position] = []
        for pos in positions_raw:
            if not isinstance(pos, list) or len(pos) != 2:
                raise ValueError(f"zone {zone_id}: position must be [x, y], got: {pos!r}")

            x, y = pos
            if not isinstance(x, int) or not isinstance(y, int):
                raise ValueError(
                    f"zone {zone_id}: position coordinates must be integers, got: {pos!r}"
                )
            positions.append(Position(x, y))

        zone = Zone.from_positions(
            id=ZoneId(zone_id),
            zone_type=zone_type,
            positions=positions,
        )
        zones.append(zone)

    return zones
