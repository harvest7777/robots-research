from __future__ import annotations

from typing import Any

from simulation_models.assignment import RobotId
from simulation_models.robot_state import RobotState


def load_robot_states(raw: list[dict[str, Any]]) -> list[RobotState]:
    """Load a list of RobotStates from raw config data.

    Args:
        raw: List of robot_state dictionaries, each with required keys:
            robot_id: Integer identifier matching a Robot.
            position: [x, y] starting position.

            Optional keys:
            battery_level: Float between 0.0 and 1.0. Defaults to 1.0.

    Returns:
        List of configured RobotState instances.

    Raises:
        KeyError: If required keys are missing.
        ValueError: If values are invalid.
    """
    robot_states: list[RobotState] = []
    seen_ids: set[int] = set()

    for i, state_raw in enumerate(raw):
        if "robot_id" not in state_raw:
            raise KeyError(f"robot_state at index {i} missing required key: 'robot_id'")
        if "position" not in state_raw:
            raise KeyError(f"robot_state at index {i} missing required key: 'position'")

        robot_id = state_raw["robot_id"]
        position_raw = state_raw["position"]

        if not isinstance(robot_id, int) or robot_id < 0:
            raise ValueError(
                f"robot_state robot_id must be a non-negative integer, got: {robot_id!r}"
            )

        if robot_id in seen_ids:
            raise ValueError(f"duplicate robot_state for robot_id: {robot_id}")
        seen_ids.add(robot_id)

        if not isinstance(position_raw, list) or len(position_raw) != 2:
            raise ValueError(
                f"robot_state {robot_id}: position must be [x, y], got: {position_raw!r}"
            )

        x, y = position_raw
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError(
                f"robot_state {robot_id}: position coordinates must be numbers, "
                f"got: {position_raw!r}"
            )

        battery_level = state_raw.get("battery_level", 1.0)
        if not isinstance(battery_level, (int, float)) or not (0.0 <= battery_level <= 1.0):
            raise ValueError(
                f"robot_state {robot_id}: battery_level must be between 0.0 and 1.0, "
                f"got: {battery_level!r}"
            )

        robot_state = RobotState(
            robot_id=RobotId(robot_id),
            x=float(x),
            y=float(y),
            battery_level=float(battery_level),
        )
        robot_states.append(robot_state)

    return robot_states
