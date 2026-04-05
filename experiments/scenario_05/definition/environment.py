# Scenario 05 — Sealed Room (Unreachable Task)
#
# A rectangular room is fully enclosed by obstacles with no entrance.
# No robot can ever reach the interior regardless of pathfinding.
#
# Sealed room perimeter:
#   Top wall:    y=2,  x=5..13
#   Bottom wall: y=6,  x=5..13
#   Left wall:   x=5,  y=3..5
#   Right wall:  x=13, y=3..5
#
# Interior (unreachable): x=6..12, y=3..5

from simulation.domain import Environment
from simulation.primitives import Position

ENVIRONMENT = Environment(width=20, height=15)

# Top and bottom walls
for x in range(5, 14):
    ENVIRONMENT.add_obstacle(Position(x, 2))
    ENVIRONMENT.add_obstacle(Position(x, 6))

# Left and right walls (excluding corners already placed)
for y in range(3, 6):
    ENVIRONMENT.add_obstacle(Position(5, y))
    ENVIRONMENT.add_obstacle(Position(13, y))
