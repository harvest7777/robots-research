from typing import Any

from simulation_models.environment import Environment
from simulation_models.position import Position


def load_environment(raw: dict[str, Any]) -> Environment:
    """Load an Environment from raw config data.

    Args:
        raw: Dictionary with 'width', 'height', and optional 'obstacles' keys.
            obstacles: Array of [x, y] positions.

    Returns:
        Configured Environment instance.

    Raises:
        KeyError: If required keys are missing.
        ValueError: If values are invalid.
    """
    if "width" not in raw:
        raise KeyError("environment config missing required key: 'width'")
    if "height" not in raw:
        raise KeyError("environment config missing required key: 'height'")

    width = raw["width"]
    height = raw["height"]

    if not isinstance(width, int) or width <= 0:
        raise ValueError(f"width must be a positive integer, got: {width!r}")
    if not isinstance(height, int) or height <= 0:
        raise ValueError(f"height must be a positive integer, got: {height!r}")

    env = Environment(width=width, height=height)

    obstacles_raw = raw.get("obstacles", [])
    seen: set[tuple[int, int]] = set()

    for obs in obstacles_raw:
        if not isinstance(obs, list) or len(obs) != 2:
            raise ValueError(f"obstacle must be [x, y], got: {obs!r}")

        x, y = obs
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError(f"obstacle coordinates must be integers, got: {obs!r}")

        if (x, y) in seen:
            continue  # Skip duplicates
        seen.add((x, y))

        env.add_obstacle(Position(x, y))

    return env
