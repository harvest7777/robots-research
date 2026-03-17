"""
step() — thin wrapper (new design)

Combines classify_step and apply_outcome into a single call.
Pure function: same inputs always produce the same outputs.
"""

from __future__ import annotations

from simulation.algorithms.movement_planner import PathfindingAlgorithm

from .applicator import apply_outcome
from .observer import classify_step
from .simulation_state import SimulationState
from .step_outcome import StepOutcome


def step(
    state: SimulationState,
    pathfinding: PathfindingAlgorithm,
) -> tuple[SimulationState, StepOutcome]:
    """Advance the simulation by one tick.

    Returns (new_state, outcome). Does not mutate the input state.
    The caller is responsible for:
    - Writing new_state to StateService
    - Appending outcome.tasks_spawned to TaskRegistry
    - Notifying listeners with outcome
    """
    outcome = classify_step(state, pathfinding)
    new_state = apply_outcome(state, outcome)
    return new_state, outcome
