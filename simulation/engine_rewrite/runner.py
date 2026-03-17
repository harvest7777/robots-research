"""
SimulationRunner (new design)

Wires the registry, assignment service, and engine step together.
Contains no business logic — only orchestration.

Each call to step():
  1. Rebuilds state.tasks from the registry so externally added and
     previously spawned tasks are visible to the observer this tick.
  2. Reads current assignments from the assignment service.
  3. Runs one engine tick (classify_step + apply_outcome).
  4. Writes tasks_spawned back to the registry so they are available
     for assignment next tick.
  5. Returns the StepOutcome for the caller to inspect or log.
"""

from __future__ import annotations

import dataclasses

from simulation.algorithms.movement_planner import PathfindingAlgorithm

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

    @property
    def state(self) -> SimulationState:
        return self._state

    def step(self) -> StepOutcome:
        # Rebuild state.tasks from the registry each tick.
        tasks = {t.id: t for t in self._registry.all()}
        current_state = dataclasses.replace(self._state, tasks=tasks)

        assignments = self._assignment_service.get_current()

        new_state, outcome = engine_step(current_state, assignments, self._pathfinding)

        for task in outcome.tasks_spawned:
            self._registry.add(task)

        self._state = new_state
        return outcome
