# Scenario 13 — Formation Requirement (MoveTask)
#
# Two cargo objects must each be carried to a destination.
# Each MoveTask requires min_robots_required=3 to advance.
# Only 5 robots are available (3+3=6 would be needed to run both in parallel).
#
# Without override: LLM may split robots across both formations (e.g. 2+3 or
# 2+2+1), leaving at least one formation perpetually short of the 3-robot
# quorum and unable to move.
#
# With override: LLM sequences the formations — assign 3 robots to one cargo
# first, complete it, then reassign those robots to the second cargo.
#
# Layout (30x15 open grid, no obstacles):
# - Cargo A starts at (3, 4),  destination (25, 4)   — top lane
# - Cargo B starts at (3, 10), destination (25, 10)  — bottom lane
# - Robots R1-R5 start clustered at x=1-2, y=4-10

from simulation.domain import Environment

ENVIRONMENT = Environment(width=30, height=15)
