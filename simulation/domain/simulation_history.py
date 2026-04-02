"""
SimulationHistoryEntry

Immutable snapshot of one simulation tick, containing the full state,
the outcome of that tick, and the LLM's assignment decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.domain.assignment import Assignment
from simulation.domain.simulation_state import SimulationState
from simulation.domain.step_outcome import StepOutcome


@dataclass(frozen=True)
class SimulationHistoryEntry:
    """
    Immutable snapshot of one simulation tick.

    Contains:
    - state: full simulation state after this tick
    - outcome: what happened this tick (moves, work, completions, etc.)
    - assignments: the LLM's assignment decisions that led to this outcome
    """

    state: SimulationState
    outcome: StepOutcome
    assignments: tuple[Assignment, ...]
