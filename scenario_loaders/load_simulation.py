from __future__ import annotations

import json
from pathlib import Path

from simulation_models.simulation import PathfindingAlgorithm, Simulation

from .load_environment import load_environment
from .load_robot_states import load_robot_states
from .load_robots import load_robots
from .load_task_states import load_task_states
from .load_tasks import load_tasks
from .load_zones import load_zones


def load_simulation_from_dict(
    data: dict,
    pathfinding_algorithm: PathfindingAlgorithm | None = None,
) -> Simulation:
    """Load a simulation scenario from an already-parsed dict.

    Same as load_simulation but skips the file read.
    """
    raw = data

    if "environment" not in raw:
        raise KeyError("scenario missing required key: 'environment'")
    env_raw = raw["environment"]
    environment = load_environment(env_raw)

    if "zones" in env_raw:
        zones = load_zones(env_raw["zones"])
        for zone in zones:
            environment.add_zone(zone)

    if "robots" not in raw:
        raise KeyError("scenario missing required key: 'robots'")
    robots = load_robots(raw["robots"])

    if "tasks" not in raw:
        raise KeyError("scenario missing required key: 'tasks'")
    tasks = load_tasks(raw["tasks"])

    if "robot_states" not in raw:
        raise KeyError("scenario missing required key: 'robot_states'")
    robot_states_list = load_robot_states(raw["robot_states"])
    robot_states = {rs.robot_id: rs for rs in robot_states_list}

    if "task_states" not in raw:
        raise KeyError("scenario missing required key: 'task_states'")
    task_states_list = load_task_states(raw["task_states"])
    task_states = {ts.task_id: ts for ts in task_states_list}

    return Simulation(
        environment=environment,
        robots=robots,
        tasks=tasks,
        robot_states=robot_states,
        task_states=task_states,
        pathfinding_algorithm=pathfinding_algorithm,
    )


def load_simulation(
    path: str | Path,
    pathfinding_algorithm: PathfindingAlgorithm | None = None,
) -> Simulation:
    """Load a simulation scenario from a JSON file.

    Args:
        path: Path to the simulation scenario JSON file.
        pathfinding_algorithm: Optional pathfinding algorithm. Can also be set
            on the returned Simulation before calling run().

    Returns:
        Configured Simulation instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If required keys are missing.
        ValueError: If config values are invalid.
    """
    with open(Path(path)) as f:
        data = json.load(f)

    return load_simulation_from_dict(data, pathfinding_algorithm=pathfinding_algorithm)
