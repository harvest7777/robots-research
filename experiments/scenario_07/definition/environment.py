# Scenario 11 — Bottleneck Congestion
#
# Small box area with a 1-wide entrance (corridor bottleneck).
# Robots line up in front of the entrance. Tasks inside the box require
# robots to pass through the bottleneck corridor.
#
# Without override: LLM mass-assigns robots to tasks inside the box,
# causing them to jam in the bottleneck corridor.
#
# With override: Limit robots in the bottleneck area to avoid congestion.
#
# Layout:
# - Box interior: x=9-13, y=4-10
# - Entrance: single cell at (8,7)
# - Corridor in front: x=7, y=6-8 (3 cells)
# - Robots start at x=2-6, y=6-8 (line in front of corridor)

from simulation.domain import Environment
from simulation.primitives import Position

ENVIRONMENT = Environment(width=20, height=15)

for x in range(8, 15):
    ENVIRONMENT.add_obstacle(Position(x, 3))
    ENVIRONMENT.add_obstacle(Position(x, 11))

for y in range(4, 11):
    ENVIRONMENT.add_obstacle(Position(14, y))

for y in range(4, 7):
    ENVIRONMENT.add_obstacle(Position(8, y))

for y in range(8, 11):
    ENVIRONMENT.add_obstacle(Position(8, y))
