"""
SimulationAnalysis

Pure value object derived from a simulation history (the sequence of
(SimulationState, StepOutcome) pairs produced by SimulationRunner.step()).

Contains no runner coupling — callers that accumulate history manually
can build this directly via from_history() without going through the runner.

Metrics
-------
total_ticks                   : number of ticks elapsed (== final state's t_now)
makespan                      : tick at which the last task completed; None if no tasks
                                ever completed
tasks_completed               : number of distinct tasks that reached DONE status
tasks_failed                  : number of distinct tasks that reached FAILED status

robot_ticks_working           : per robot — ticks the robot contributed work to a task
robot_ticks_moving            : per robot — ticks the robot moved toward its assignment
robot_ticks_idle              : per robot — ticks the robot was neither working nor moving
robot_ticks_stuck             : per robot — ticks the robot intended to move but was
                                blocked in place by collision resolution
robot_battery_remaining       : per robot — battery level at end of run (1.0 = full, 0.0 = dead)

task_ticks_to_complete        : per completed WorkTask — ticks from first work applied
                                to completion (completed_at - started_at)
task_ticks_actively_worked    : per task — ticks where at least one robot worked on it
work_tasks_never_started_count: WorkTasks in the final state that were never worked on
                                (started_at is None, not terminal)

assignment_ignores_by_reason  : total ignored assignments per IgnoreReason across the run
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from simulation.domain.base_task import TaskId, TaskStatus
from simulation.domain.robot_state import RobotId
from simulation.domain.step_outcome import IgnoreReason, StepOutcome
from simulation.domain.task_state import TaskState

from simulation.domain.simulation_state import SimulationState


@dataclass(frozen=True)
class SimulationAnalysis:
    total_ticks: int
    makespan: int | None
    tasks_completed: int
    tasks_failed: int

    # Robot utilization
    robot_ticks_working:        dict[RobotId, int]
    robot_ticks_moving:         dict[RobotId, int]
    robot_ticks_idle:           dict[RobotId, int]
    robot_ticks_stuck:          dict[RobotId, int]
    robot_battery_remaining:    dict[RobotId, float]

    # Task progress
    task_ticks_to_complete:         dict[TaskId, int]
    task_ticks_actively_worked:     dict[TaskId, int]
    work_tasks_never_started_count: int

    # Assignment quality
    assignment_ignores_by_reason: dict[IgnoreReason, int]

    @classmethod
    def from_history(
        cls,
        history: list[tuple[SimulationState, StepOutcome]],
    ) -> SimulationAnalysis:
        if not history:
            return cls(
                total_ticks=0,
                makespan=None,
                tasks_completed=0,
                tasks_failed=0,
                robot_ticks_working={},
                robot_ticks_moving={},
                robot_ticks_idle={},
                robot_ticks_stuck={},
                robot_battery_remaining={},
                task_ticks_to_complete={},
                task_ticks_actively_worked={},
                work_tasks_never_started_count=0,
                assignment_ignores_by_reason={},
            )

        final_state, _ = history[-1]
        total_ticks = final_state.t_now.tick

        # --- tasks completed / failed ---
        completed_ids: set[TaskId] = set()
        for _, outcome in history:
            completed_ids.update(outcome.tasks_completed)

        failed_ids: set[TaskId] = {
            task_id
            for task_id, ts in final_state.task_states.items()
            if ts.status == TaskStatus.FAILED
        }

        makespan: int | None = None
        if completed_ids:
            completion_ticks = [
                ts.completed_at.tick
                for tid in completed_ids
                if (ts := final_state.task_states.get(tid)) is not None
                and ts.completed_at is not None
            ]
            if completion_ticks:
                makespan = max(completion_ticks)

        # --- robot utilization ---
        robot_ticks_working:  dict[RobotId, int] = defaultdict(int)
        robot_ticks_moving:   dict[RobotId, int] = defaultdict(int)
        robot_ticks_stuck:    dict[RobotId, int] = defaultdict(int)
        task_ticks_worked_by: dict[TaskId, set[int]] = defaultdict(set)  # task_id -> set of tick indices

        assignment_ignores_by_reason: dict[IgnoreReason, int] = defaultdict(int)

        for tick_index, (_, outcome) in enumerate(history):
            robots_active_this_tick: set[RobotId] = set()

            for robot_id, _task_id in outcome.worked:
                robot_ticks_working[robot_id] += 1
                robots_active_this_tick.add(robot_id)

            for robot_id, _position in outcome.moved:
                robot_ticks_moving[robot_id] += 1
                robots_active_this_tick.add(robot_id)

            for robot_id in outcome.robots_stuck:
                robot_ticks_stuck[robot_id] += 1

            for robot_id, task_id in outcome.worked:
                task_ticks_worked_by[task_id].add(tick_index)

            for assignment, reason in outcome.assignments_ignored:
                assignment_ignores_by_reason[reason] += 1

        # idle = ticks where the robot appeared in neither worked nor moved
        robot_ticks_idle: dict[RobotId, int] = {}
        for robot_id in final_state.robot_states:
            worked = robot_ticks_working.get(robot_id, 0)
            moved  = robot_ticks_moving.get(robot_id, 0)
            # a robot can be in both worked and moved the same tick if it's
            # within tolerance range but not at the exact goal cell, so cap at total_ticks
            robot_ticks_idle[robot_id] = max(0, total_ticks - worked - moved)

        robot_battery_remaining: dict[RobotId, float] = {
            robot_id: rs.battery_level
            for robot_id, rs in final_state.robot_states.items()
        }

        # --- task progress ---
        task_ticks_to_complete: dict[TaskId, int] = {}
        for task_id in completed_ids:
            ts = final_state.task_states.get(task_id)
            if isinstance(ts, TaskState) and ts.started_at is not None and ts.completed_at is not None:
                task_ticks_to_complete[task_id] = ts.completed_at.tick - ts.started_at.tick

        task_ticks_actively_worked: dict[TaskId, int] = {
            task_id: len(ticks)
            for task_id, ticks in task_ticks_worked_by.items()
        }

        work_tasks_never_started_count = sum(
            1
            for ts in final_state.task_states.values()
            if isinstance(ts, TaskState)
            and ts.status not in (TaskStatus.DONE, TaskStatus.FAILED)
            and ts.started_at is None
        )

        return cls(
            total_ticks=total_ticks,
            makespan=makespan,
            tasks_completed=len(completed_ids),
            tasks_failed=len(failed_ids),
            robot_ticks_working=dict(robot_ticks_working),
            robot_ticks_moving=dict(robot_ticks_moving),
            robot_ticks_idle=robot_ticks_idle,
            robot_ticks_stuck=dict(robot_ticks_stuck),
            robot_battery_remaining=robot_battery_remaining,
            task_ticks_to_complete=task_ticks_to_complete,
            task_ticks_actively_worked=task_ticks_actively_worked,
            work_tasks_never_started_count=work_tasks_never_started_count,
            assignment_ignores_by_reason=dict(assignment_ignores_by_reason),
        )
