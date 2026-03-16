"""
Applicator — apply_outcome (new design)

Pure function that takes current state and a StepOutcome and returns new state.
No business rules. No validity checks. Just applies what classify_step decided.

Derived state updates (not in StepOutcome, computed here):
- Battery drain: move rate for moved robots, work rate for worked robots,
  idle rate for everyone else.
- Idle robots: any robot not in moved or worked.
- t_now advances by 1 tick.
"""

from __future__ import annotations

import copy

from simulation.domain.base_task import TaskId, TaskStatus
from simulation.domain.rescue_point import RescuePointId
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.search_task import SearchTaskState
from simulation.domain.task import Task, TaskType
from simulation.domain.task_state import TaskState
from simulation.primitives.time import Time

from .simulation_state import SimulationState
from .step_outcome import StepOutcome

# Battery drain rates — mirrors robot.py constants
_DRAIN_MOVE = 0.001
_DRAIN_WORK = 0.002
_DRAIN_IDLE = 0.0005


def apply_outcome(state: SimulationState, outcome: StepOutcome) -> SimulationState:
    """Apply a StepOutcome to state and return the new state for the next tick.

    Pure function — does not mutate the input state.
    """
    moved_robots: set[RobotId] = {rid for rid, _ in outcome.moved}
    worked_robots: set[RobotId] = {rid for rid, _ in outcome.worked}

    # --- Robot states ---------------------------------------------------------
    new_robot_states: dict[RobotId, RobotState] = {}
    for rid, rs in state.robot_states.items():
        new_rs = copy.copy(rs)
        if rid in moved_robots:
            new_pos = next(pos for r, pos in outcome.moved if r == rid)
            new_rs.position = new_pos
            new_rs.battery_level = max(0.0, rs.battery_level - _DRAIN_MOVE)
        elif rid in worked_robots:
            new_rs.battery_level = max(0.0, rs.battery_level - _DRAIN_WORK)
        else:
            new_rs.battery_level = max(0.0, rs.battery_level - _DRAIN_IDLE)
        if rid in outcome.waypoints:
            new_rs.current_waypoint = outcome.waypoints[rid]
        new_robot_states[rid] = new_rs

    # --- Task states ----------------------------------------------------------
    new_task_states = dict(state.task_states)

    # Apply work progress
    work_by_task: dict[TaskId, int] = {}
    for rid, task_id in outcome.worked:
        work_by_task[task_id] = work_by_task.get(task_id, 0) + 1

    for task_id, ticks in work_by_task.items():
        ts = new_task_states[task_id]
        assert isinstance(ts, TaskState)
        new_ts = copy.copy(ts)
        if new_ts.started_at is None:
            new_ts.started_at = state.t_now
        new_ts.work_done = Time(new_ts.work_done.tick + ticks)
        new_task_states[task_id] = new_ts

    # Apply rescue point discoveries to SearchTaskState
    for search_task_id, rp_id in outcome.rescue_points_found:
        ts = new_task_states[search_task_id]
        assert isinstance(ts, SearchTaskState)
        new_ts = SearchTaskState(
            task_id=ts.task_id,
            status=ts.status,
            completed_at=ts.completed_at,
            rescue_found={**ts.rescue_found, rp_id: True},
        )
        new_task_states[search_task_id] = new_ts

    # Mark completed tasks
    new_t = state.t_now + Time(1)
    for task_id in outcome.tasks_completed:
        ts = new_task_states[task_id]
        new_ts = copy.copy(ts)
        new_ts.status = TaskStatus.DONE
        new_ts.completed_at = new_t
        new_task_states[task_id] = new_ts

    # --- Add spawned tasks ----------------------------------------------------
    new_tasks = dict(state.tasks)
    new_task_states_for_spawned: dict[TaskId, TaskState] = {}
    for task in outcome.tasks_spawned:
        new_tasks[task.id] = task
        new_task_states_for_spawned[task.id] = TaskState(task_id=task.id)
    new_task_states.update(new_task_states_for_spawned)

    return SimulationState(
        environment=state.environment,
        robots=state.robots,
        robot_states=new_robot_states,
        tasks=new_tasks,
        task_states=new_task_states,
        t_now=new_t,
    )
