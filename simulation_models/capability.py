"""
Robot Capabilities

This module defines the capabilities that robots may possess. Capabilities describe
what a robot can do, not what type of robot it is.

Capabilities are used for task-robot matching: a task declares which capabilities
it requires, and only robots possessing all required capabilities may be assigned.

Design notes:
- Capabilities are orthogonal: a robot may have any combination
- Capabilities are static: they do not change during simulation
- Capabilities describe potential, not current state (e.g., CHARGING means
  the robot can charge others, not that it is currently charging)
"""

from enum import Enum


class Capability(Enum):
    """
    Robot capabilities required to perform tasks.

    Each capability represents a distinct functional ability:

    VISION
        Optical sensing for inspection, navigation, and anomaly detection.
        Required for tasks involving visual assessment or image capture.

    MANIPULATION
        Physical interaction with objects (gripping, moving, assembling).
        Required for tasks involving material handling or assembly.

    SENSING
        Environmental data collection beyond vision (temperature, pressure,
        chemical, acoustic). Required for diagnostic or monitoring tasks.

    REPAIR
        Ability to perform maintenance and repair operations on equipment
        or other robots. Required for maintenance tasks.

    CHARGING
        Ability to transfer power to other robots or equipment.
        Required for mobile charging or power delivery tasks.
    """

    VISION = "vision"
    MANIPULATION = "manipulation"
    SENSING = "sensing"
    REPAIR = "repair"
    CHARGING = "charging"
