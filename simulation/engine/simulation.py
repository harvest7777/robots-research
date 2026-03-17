"""
Simulation State Container

The Simulation class holds all state and data needed to run a simulation:
- Environment (grid, zones, obstacles)
- Robots (immutable definitions)
- Tasks (immutable definitions — Task and SearchTask)
- Robot states (mutable, keyed by robot_id)
- Task states (mutable, keyed by task_id — TaskState or SearchTaskState)
- Assignment algorithm (configurable by researchers)
- Time tracking (t_now, dt) and snapshot history
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable

from simulation.domain.assignment import Assignment
from simulation.domain.base_task import BaseTask, BaseTaskState, TaskId, mark_done
from simulation.domain.environment import Environment
from simulation.primitives.position import Position
from simulation.domain.rescue_point import RescuePoint
from simulation.domain.robot import Robot, move_robot, work_robot, idle_robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.search_task import SearchTask, SearchTaskState
from simulation.domain.task import Task, TaskType
from simulation.domain.task_state import TaskState, apply_work
from simulation.engine.base_assignment_service import BaseAssignmentService
from simulation.engine.simulation_result import SimulationResult
from simulation.engine.snapshot import SimulationSnapshot
from simulation.primitives.time import Time
from simulation.algorithms.movement_planner import PathfindingAlgorithm, plan_moves, resolve_collisions, resolve_task_target_position
from simulation.domain.step_context import StepContext
from simulation.algorithms.search_phase_handler import SearchEffect, compute_search_phase_effect
from simulation.algorithms.search_goal import compute_search_goal
from simulation.algorithms.work_eligibility import filter_assignments_for_eligible_robots


@dataclass
class Simulation:
    """
    Central container for simulation state and data.

    Attributes:
        environment: The grid environment with zones and obstacles.
        robots: List of robot definitions (immutable).
        tasks: List of task definitions (immutable — Task or SearchTask).
        robot_states: Mutable state for each robot, keyed by robot_id.
        task_states: Mutable state for each task, keyed by task_id.
        assignment_service: Source of active robot-task assignments.
        pathfinding_algorithm: Algorithm for computing robot movement.
        t_now: Current simulation time.
        dt: Time step size per step() call.
        history: Snapshot history keyed by simulation time.
    """

    environment: Environment
    robots: list[Robot]
    tasks: list[BaseTask]
    robot_states: dict[RobotId, RobotState]
    task_states: dict[TaskId, BaseTaskState]
    assignment_service: BaseAssignmentService | None = None
    pathfinding_algorithm: PathfindingAlgorithm | None = None
    t_now: Time = field(default_factory=lambda: Time(0))
    dt: Time = field(default_factory=lambda: Time(0))
    history: dict[Time, SimulationSnapshot] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._robot_by_id: dict[RobotId, Robot] = {r.id: r for r in self.robots}
        self._task_by_id: dict[TaskId, BaseTask] = {t.id: t for t in self.tasks}
        self.history[self.t_now] = self.snapshot([])

    def _validate_ready(self) -> None:
        if self.pathfinding_algorithm is None:
            raise ValueError(
                "Simulation requires 'pathfinding_algorithm' before stepping"
            )

    def run(
        self,
        max_delta_time: Time,
        on_tick: Callable[[SimulationSnapshot], None] | None = None,
    ) -> SimulationResult:
        """Run the simulation to completion or until the time budget is exhausted."""
        self._validate_ready()

        t_start = self.t_now
        from simulation.domain.base_task import TaskStatus
        terminal = {TaskStatus.DONE, TaskStatus.FAILED}

        # IDLE tasks never complete — exclude from termination check.
        # SearchTask IS included: if no rescue is ever found it stays non-terminal
        # and the budget exhausts, which is correct behaviour.
        non_idle_task_ids = {
            t.id for t in self.tasks
            if not (isinstance(t, Task) and t.type == TaskType.IDLE)
        }

        while (self.t_now - t_start) < max_delta_time:
            if all(self.task_states[tid].status in terminal for tid in non_idle_task_ids):
                break
            self._step()
            if on_tick is not None:
                on_tick(self.history[self.t_now])

        all_terminal = all(self.task_states[tid].status in terminal for tid in non_idle_task_ids)
        tasks_succeeded = sum(
            1 for tid in non_idle_task_ids if self.task_states[tid].status == TaskStatus.DONE
        )

        return SimulationResult(
            completed=all_terminal,
            tasks_succeeded=tasks_succeeded,
            tasks_total=len(non_idle_task_ids),
            makespan=self.dt if all_terminal else None,
            snapshots=list(self.history.values()),
        )

    def _step(self) -> None:
        """Execute one simulation tick."""
        self.dt += Time(1)
        self.t_now = self.t_now + Time(1)

        assignments = self._get_active_assignments()
        ctx = self._build_step_context(assignments)
        planned_moves = self._plan_robot_moves(ctx)
        planned_moves = self._resolve_robot_collisions(planned_moves)

        discoveries = self._find_rescue_discoveries(ctx)
        if discoveries:
            search_task_states = {
                tid: s for tid, s in self.task_states.items()
                if isinstance(s, SearchTaskState)
            }
            effect = compute_search_phase_effect(
                discoveries=discoveries,
                all_assignments=assignments,
                search_task_states=search_task_states,
                task_by_id=self._task_by_id,
                all_rescue_points=self.environment.rescue_points,
                t_now=self.t_now,
            )
            self._apply_search_effect(effect)

        moved_set = self._apply_robot_moves(planned_moves)
        eligible_by_task = self._snapshot_work_eligibility(ctx)
        self._advance_task_progress(eligible_by_task)
        worked_set = self._apply_robot_work(eligible_by_task, moved_set)
        self._mark_idle_robots(moved_set, worked_set)

        self.history[self.t_now] = self.snapshot(assignments)

    def _build_step_context(self, assignments: list[Assignment]) -> StepContext:
        return StepContext(
            robot_states=self.robot_states,
            task_states=self.task_states,
            assignments=assignments,
            robot_by_id=self._robot_by_id,
            task_by_id=self._task_by_id,
            environment=self.environment,
            t_now=self.t_now,
        )

    def _plan_robot_moves(self, ctx: StepContext) -> dict[RobotId, Position | None]:
        robot_to_task = {rid: a.task_id for a in ctx.assignments for rid in a.robot_ids}

        def _goal_resolver(robot_id: RobotId, state: RobotState) -> Position | None:
            task = self._task_by_id[robot_to_task[robot_id]]
            if isinstance(task, SearchTask):
                search_state = self.task_states[task.id]
                assert isinstance(search_state, SearchTaskState)
                goal = compute_search_goal(
                    state,
                    self.environment.rescue_points,
                    search_state.rescue_found,
                    task.proximity_threshold,
                    self.pathfinding_algorithm,
                    self.environment,
                )
                state.current_waypoint = goal
                return goal
            assert isinstance(task, Task)
            return resolve_task_target_position(task, state.position, self.environment)

        return plan_moves(ctx, self.pathfinding_algorithm, _goal_resolver)

    def _resolve_robot_collisions(
        self, planned_moves: dict[RobotId, Position | None]
    ) -> dict[RobotId, Position | None]:
        current_positions: dict[RobotId, Position] = {
            robot_id: state.position for robot_id, state in self.robot_states.items()
        }
        return resolve_collisions(planned_moves, current_positions)

    def _find_rescue_discoveries(
        self, ctx: StepContext
    ) -> list[tuple[RobotId, RescuePoint, TaskId]]:
        """Return (robot_id, rescue_point, search_task_id) for each discovery this tick.

        A rescue point can only be discovered once per tick (first robot wins,
        lowest robot_id for determinism). Already-found rescue points are skipped.
        """
        discovered: list[tuple[RobotId, RescuePoint, TaskId]] = []
        seen_rescue_ids: set[TaskId] = set()

        search_assignments = [
            (a, a.task_id)
            for a in ctx.assignments
            if isinstance(self._task_by_id.get(a.task_id), SearchTask)
        ]

        for assignment, search_task_id in search_assignments:
            search_state = self.task_states[search_task_id]
            assert isinstance(search_state, SearchTaskState)

            for robot_id in sorted(assignment.robot_ids):
                state = self.robot_states[robot_id]
                for rescue_point in self.environment.rescue_points.values():
                    if search_state.rescue_found.get(rescue_point.id):
                        continue
                    if rescue_point.id in seen_rescue_ids:
                        continue
                    if state.position == rescue_point.position:
                        discovered.append((robot_id, rescue_point, search_task_id))
                        seen_rescue_ids.add(rescue_point.id)
                        break

        return discovered

    def _apply_search_effect(self, effect: SearchEffect) -> None:
        """Apply a SearchEffect to live simulation state."""
        for search_task_id, found_updates in effect.rescue_found_updates.items():
            state = self.task_states[search_task_id]
            assert isinstance(state, SearchTaskState)
            state.rescue_found.update(found_updates)

        if self.assignment_service is not None:
            self.assignment_service.add_assignments(effect.new_assignments)

        for robot_id in effect.waypoints_to_clear:
            self.robot_states[robot_id].current_waypoint = None

        for task_id in effect.search_task_ids_to_mark_done:
            mark_done(self.task_states[task_id], self.t_now)

    def _apply_robot_moves(
        self, planned_moves: dict[RobotId, Position | None]
    ) -> set[RobotId]:
        moved_set: set[RobotId] = set()
        for robot_id, next_pos in planned_moves.items():
            if next_pos is None:
                continue
            move_robot(self.robot_states[robot_id], next_pos)
            moved_set.add(robot_id)
        return moved_set

    def _snapshot_work_eligibility(self, ctx: StepContext) -> dict[TaskId, list[RobotId]]:
        """Snapshot which robots are eligible to work on each task this tick.

        SearchTask and IDLE tasks never accumulate work and are skipped.
        """
        result: dict[TaskId, list[RobotId]] = {}
        for task in self.tasks:
            if isinstance(task, SearchTask):
                result[task.id] = []
            elif isinstance(task, Task) and task.type == TaskType.IDLE:
                result[task.id] = []
            else:
                assert isinstance(task, Task)
                result[task.id] = filter_assignments_for_eligible_robots(task, ctx)
        return result

    def _advance_task_progress(
        self, eligible_by_task: dict[TaskId, list[RobotId]]
    ) -> None:
        for task in self.tasks:
            eligible = eligible_by_task[task.id]
            if not eligible:
                continue
            assert isinstance(task, Task)
            apply_work(
                self.task_states[task.id],  # type: ignore[arg-type]
                task.required_work_time,
                Time(len(eligible)),
                self.t_now,
            )

    def _apply_robot_work(
        self,
        eligible_by_task: dict[TaskId, list[RobotId]],
        moved_set: set[RobotId],
    ) -> set[RobotId]:
        worked_set: set[RobotId] = set()
        for task in self.tasks:
            for robot_id in eligible_by_task[task.id]:
                if robot_id not in moved_set:
                    work_robot(self.robot_states[robot_id])
                    worked_set.add(robot_id)
        return worked_set

    def _mark_idle_robots(
        self, moved_set: set[RobotId], worked_set: set[RobotId]
    ) -> None:
        for robot_id, state in self.robot_states.items():
            if robot_id not in moved_set and robot_id not in worked_set:
                idle_robot(state)

    def _get_active_assignments(self) -> list[Assignment]:
        if self.assignment_service is None:
            return []
        return self.assignment_service.get_assignments_for_time(self.t_now)

    def snapshot(self, active_assignments: list[Assignment] | None = None) -> SimulationSnapshot:
        """Create a read-only snapshot of current simulation state."""
        if active_assignments is None:
            active_assignments = (
                self.assignment_service.get_assignments_for_time(self.t_now)
                if self.assignment_service is not None
                else []
            )

        robot_states_copy = {
            rid: dataclasses.replace(state)
            for rid, state in self.robot_states.items()
        }

        task_states_copy: dict[TaskId, BaseTaskState] = {}
        for tid, state in self.task_states.items():
            if isinstance(state, SearchTaskState):
                task_states_copy[tid] = SearchTaskState(
                    task_id=state.task_id,
                    status=state.status,
                    completed_at=state.completed_at,
                    rescue_found=dict(state.rescue_found),
                )
            else:
                assert isinstance(state, TaskState)
                task_states_copy[tid] = TaskState(
                    task_id=state.task_id,
                    status=state.status,
                    completed_at=state.completed_at,
                    work_done=state.work_done,
                    started_at=state.started_at,
                )

        return SimulationSnapshot(
            env=self.environment,
            robots=tuple(self.robots),
            robot_states=MappingProxyType(robot_states_copy),
            tasks=tuple(self.tasks),
            task_states=MappingProxyType(task_states_copy),
            t_now=self.t_now,
            active_assignments=tuple(active_assignments),
        )
