from __future__ import annotations

from typing import Any

from simulation_models.assignment import RobotId
from simulation_models.capability import Capability
from simulation_models.robot import Robot


def load_robots(raw: list[dict[str, Any]]) -> list[Robot]:
    """Load a list of Robots from raw config data.

    Args:
        raw: List of robot dictionaries, each with required keys:
            id: Unique integer identifier for the robot.
            capabilities: Array of capability strings.
            speed: Positive float for movement speed.

    Returns:
        List of configured Robot instances.

    Raises:
        KeyError: If required keys are missing.
        ValueError: If values are invalid.
    """
    robots: list[Robot] = []
    seen_ids: set[int] = set()

    for i, robot_raw in enumerate(raw):
        if "id" not in robot_raw:
            raise KeyError(f"robot at index {i} missing required key: 'id'")
        if "capabilities" not in robot_raw:
            raise KeyError(f"robot at index {i} missing required key: 'capabilities'")
        if "speed" not in robot_raw:
            raise KeyError(f"robot at index {i} missing required key: 'speed'")

        robot_id = robot_raw["id"]
        caps_raw = robot_raw["capabilities"]
        speed = robot_raw["speed"]

        if not isinstance(robot_id, int) or robot_id < 0:
            raise ValueError(f"robot id must be a non-negative integer, got: {robot_id!r}")

        if robot_id in seen_ids:
            raise ValueError(f"duplicate robot id: {robot_id}")
        seen_ids.add(robot_id)

        if not isinstance(caps_raw, list):
            raise ValueError(f"robot {robot_id}: capabilities must be a list")

        capabilities: list[Capability] = []
        for cap_str in caps_raw:
            try:
                capabilities.append(Capability(cap_str))
            except ValueError:
                valid_caps = [c.value for c in Capability]
                raise ValueError(
                    f"robot {robot_id}: invalid capability: {cap_str!r}, "
                    f"must be one of {valid_caps}"
                )

        if not isinstance(speed, (int, float)) or speed <= 0:
            raise ValueError(
                f"robot {robot_id}: speed must be a positive number, got: {speed!r}"
            )

        robot = Robot(
            id=RobotId(robot_id),
            capabilities=frozenset(capabilities),
            speed=float(speed),
        )
        robots.append(robot)

    return robots
