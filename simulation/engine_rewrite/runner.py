"""
SimulationRunner (new design)

Wires the registry, assignment service, and engine step together.
Contains no business logic — only orchestration.

Each call to step():
  1. Rebuilds state.tasks from the registry and stamps current assignments
     from the service into state, so the snapshot is complete before the
     engine sees it.
  2. Runs one engine tick (classify_step + apply_outcome).
  3. Writes tasks_spawned back to the registry so they are available
     for assignment next tick.
  4. Returns (SimulationState, StepOutcome) — state is the full snapshot
     for rendering; outcome is the event delta for reactive consumers.
"""

from __future__ import annotations

import dataclasses

from simulation.algorithms.movement_planner import PathfindingAlgorithm

from .analysis import SimulationAnalysis
from .services.base_assignment_service import BaseAssignmentService
from .services.base_task_registry import BaseTaskRegistry
from .simulation_state import SimulationState
from .step import step as engine_step
from .step_outcome import StepOutcome


class SimulationRunner:

    def __init__(
        self,
        state: SimulationState,
        registry: BaseTaskRegistry,
        assignment_service: BaseAssignmentService,
        pathfinding: PathfindingAlgorithm,
    ) -> None:
        self._state = state
        self._registry = registry
        self._assignment_service = assignment_service
        self._pathfinding = pathfinding
        self._history: list[tuple[SimulationState, StepOutcome]] = []

    def step(self) -> tuple[SimulationState, StepOutcome]:
        # Rebuild state.tasks from the registry each tick.
        # Pretty hacky solution tbh, but this is the one place outside
        # the applicator which state is "mutated"
        tasks = {t.id: t for t in self._registry.all()}
        assignments = self._assignment_service.get_current()
        current_state = dataclasses.replace(
            self._state,
            tasks=tasks,
            assignments=tuple(assignments),
        )

        new_state, outcome = engine_step(current_state, self._pathfinding)

        for task in outcome.tasks_spawned:
            self._registry.add(task)

        self._state = new_state
        self._history.append((new_state, outcome))
        return new_state, outcome

    def report(self) -> SimulationAnalysis:
        return SimulationAnalysis.from_history(self._history)
