from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .load_environment import load_environment
from .load_robot_states import load_robot_states
from .load_robots import load_robots
from .load_task_states import load_task_states
from .load_tasks import load_tasks
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

    if "tasks" in raw:
        tasks = load_tasks(raw["tasks"])

    if "task_states" in raw:
        task_states = load_task_states(raw["task_states"])

    if "robots" in raw:
        robots = load_robots(raw["robots"])
        print(robots)

    if "robot_states" in raw:
        robot_states = load_robot_states(raw["robot_states"])
        print(robot_states)

    return None
