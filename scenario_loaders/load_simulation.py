from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .load_environment import load_environment
from .load_zones import load_zones


def load_simulation(path: str | Path) -> None:
    """Load a simulation scenario from a JSON file.

    Args:
        path: Path to the simulation scenario JSON file.

    Returns:
        # TODO: Make this return an actual Simulation, returns None now.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If required config keys are missing.
        ValueError: If config values are invalid.
    """
    path = Path(path)

    with open(path) as f:
        raw = json.load(f)

    if "environment" in raw:
        env_raw = raw["environment"]
        env = load_environment(env_raw)

        if "zones" in env_raw:
            zones = load_zones(env_raw["zones"])
            for zone in zones:
                env.add_zone(zone)
    return None
