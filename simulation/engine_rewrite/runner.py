"""
SimulationRunner (new design)

Wires the store, assignment service, and engine step together.
Contains no business logic — only orchestration.

Each call to step():
  1. Reads robot/task definitions and runtime state from the store, then stamps
     current assignments from the assignment service into a SimulationState
     snapshot.
  2. Runs one engine tick (classify_step + apply_outcome) on the immutable snapshot.
  3. Writes updated robot_states and task_states back to the store.
  4. Registers any tasks_spawned with the store so they are available for
     assignment next tick.
  5. Returns (SimulationState, StepOutcome) — state is the full snapshot for
     rendering; outcome is the event delta for reactive consumers.
"""

from __future__ import annotations

import os

from simulation.algorithms.movement_planner import PathfindingAlgorithm
from simulation_view.base_simulation_view import BaseViewService
from simulation.algorithms.astar_pathfinding import astar_pathfind
from simulation.domain.environment import Environment
from simulation.primitives.time import Time

from ._analysis import SimulationAnalysis
from .services.base_assignment_service import BaseAssignmentService
from .services.base_simulation_store import BaseSimulationStore
from simulation.domain.simulation_state import SimulationState
from ._step import step as engine_step
from simulation.domain.step_outcome import StepOutcome


class SimulationRunner:

    def __init__(
        self,
        environment: Environment,
        store: BaseSimulationStore,
        assignment_service: BaseAssignmentService,
        pathfinding: PathfindingAlgorithm = astar_pathfind,
        view_service: BaseViewService | None = None,
    ) -> None:
        self._environment = environment
        self._store = store
        self._assignment_service = assignment_service
        self._pathfinding = pathfinding
        self._t_now: Time = Time(0)
        self._history: list[tuple[SimulationState, StepOutcome]] = []
        self._view_service = view_service

    def step(self) -> tuple[SimulationState, StepOutcome]:
        robot_states, task_states = self._store.get_snapshot()
        tasks = {t.id: t for t in self._store.all_tasks()}
        robots = {r.id: r for r in self._store.all_robots()}
        assignments = self._assignment_service.get_current()

        current_state = SimulationState(
            environment=self._environment,
            robots=robots,
            robot_states=robot_states,
            tasks=tasks,
            task_states=task_states,
            t_now=self._t_now,
            assignments=tuple(assignments),
        )

        new_state, outcome = engine_step(current_state, self._pathfinding)

        for task, state in outcome.tasks_spawned:
            self._store.add_task(task, state)

        self._store.apply(new_state.robot_states, new_state.task_states)
        self._t_now = new_state.t_now

        self._history.append((new_state, outcome))

        if self._view_service:
            self._view_service.render(new_state)

        return new_state, outcome

    def stop(self) -> SimulationAnalysis:
        if self._view_service:
            self._view_service.handle_exit()
        return self._report()

    def _report(self) -> SimulationAnalysis:
        return SimulationAnalysis.from_history(self._history)
