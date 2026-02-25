"""
Result of a completed simulation run.

Returned by Simulation.run() after the simulation terminates, either because
all tasks reached a terminal state (DONE or FAILED) or the step limit was hit.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation_models.snapshot import SimulationSnapshot


@dataclass
class SimulationResult:
    """
    Outcome of a single simulation run.

    Attributes:
        completed: True if all tasks reached a terminal state before max_steps.
        tasks_succeeded: Number of tasks that reached DONE status.
        tasks_total: Total number of tasks in the scenario.
        makespan: Steps taken to complete all tasks. None if timed out.
        snapshots: Ordered list of snapshots, one per step including step 0.
    """

    completed: bool
    tasks_succeeded: int
    tasks_total: int
    makespan: int | None
    snapshots: list[SimulationSnapshot]
