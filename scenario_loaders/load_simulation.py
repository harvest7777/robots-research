import json
from pathlib import Path
from typing import Any

from .load_environment import load_environment


def load_simulation(path: str | Path) -> dict[str, Any]:
    """Load a simulation scenario from a JSON file.

    Args:
        path: Path to the simulation scenario JSON file.

    Returns:
        Dictionary containing loaded simulation components.
        Currently returns: {"environment": Environment}

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If required config keys are missing.
        ValueError: If config values are invalid.
    """
    path = Path(path)

    with open(path) as f:
        raw = json.load(f)

    result: dict[str, Any] = {}

    if "environment" in raw:
        result["environment"] = load_environment(raw["environment"])

    return result
