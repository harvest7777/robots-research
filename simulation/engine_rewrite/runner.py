"""
SimulationRunner (new design)

Wires the registry, state service, assignment service, and engine step together.
Contains no business logic — only orchestration.

Each call to step():
  1. Reads robot/task definitions from the registry and runtime state from the
     state service, then stamps current assignments from the assignment service
     into a SimulationState snapshot.
  2. Runs one engine tick (classify_step + apply_outcome) on the immutable snapshot.
  3. Writes updated robot_states and task_states back to the state service.
  4. Writes tasks_spawned back to the registry so they are available for
     assignment next tick.
  5. Returns (SimulationState, StepOutcome) — state is the full snapshot for
     rendering; outcome is the event delta for reactive consumers.
"""

from __future__ import annotations

from simulation.algorithms.movement_planner import PathfindingAlgorithm
from simulation.domain.base_task import BaseTask, BaseTaskState
from simulation.domain.environment import Environment
from simulation.domain.robot import Robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.primitives.time import Time

from ._analysis import SimulationAnalysis
from .services.base_assignment_service import BaseAssignmentService
from .services.base_simulation_registry import BaseSimulationRegistry
from .services.base_simulation_state_service import BaseSimulationStateService
from .simulation_state import SimulationState
from ._step import step as engine_step
from .step_outcome import StepOutcome


class SimulationRunner:

    def __init__(
        self,
        environment: Environment,
        registry: BaseSimulationRegistry,
        state_service: BaseSimulationStateService,
        assignment_service: BaseAssignmentService,
        pathfinding: PathfindingAlgorithm,
    ) -> None:
        self._environment = environment
        self._registry = registry
        self._state_service = state_service
        self._assignment_service = assignment_service
        self._pathfinding = pathfinding
        self._t_now: Time = Time(0)
        self._history: list[tuple[SimulationState, StepOutcome]] = []

    def add_robot(self, robot: Robot, initial_state: RobotState) -> None:
        """Register a robot definition and its initial runtime state."""
        self._registry.add_robot(robot)
        self._state_service.init_robot(robot.id, initial_state)

    def add_task(self, task: BaseTask, initial_state: BaseTaskState | None = None) -> None:
        """Register a task definition and its initial runtime state.

        If initial_state is omitted, task.initial_state() is called. MoveTask
        always requires an explicit initial_state (its starting position must
        be specified by the caller).
        """
        self._registry.add_task(task)
        state = initial_state if initial_state is not None else task.initial_state()
        self._state_service.init_task(task.id, state)

    def step(self) -> tuple[SimulationState, StepOutcome]:
        robot_states, task_states = self._state_service.get_snapshot()
        tasks = {t.id: t for t in self._registry.all_tasks()}
        robots = {r.id: r for r in self._registry.all_robots()}
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

        for task in outcome.tasks_spawned:
            self.add_task(task)

        self._state_service.apply(new_state.robot_states, new_state.task_states)
        self._t_now = new_state.t_now

        self._history.append((new_state, outcome))
        return new_state, outcome

    def report(self) -> SimulationAnalysis:
        return SimulationAnalysis.from_history(self._history)
