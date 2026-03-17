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
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.search_task import SearchTaskState
from simulation.domain.task import Task, TaskType
from simulation.domain.task_state import TaskState
from simulation.primitives.time import Time

from .simulation_state import SimulationState
from .step_outcome import StepOutcome


def apply_outcome(state: SimulationState, outcome: StepOutcome) -> SimulationState:
    """Apply a StepOutcome to state and return the new state for the next tick.

    Pure function — does not mutate the input state.
    """
    new_time = state.t_now + Time(1)

    moved_robots: set[RobotId] = {robot_id for robot_id, _ in outcome.moved}
    worked_robots: set[RobotId] = {robot_id for robot_id, _ in outcome.worked}

    # --- Robot states ---------------------------------------------------------
    new_robot_states: dict[RobotId, RobotState] = {}
    for robot_id, robot_state in state.robot_states.items():
        robot = state.robots[robot_id]
        new_robot_state = copy.copy(robot_state)
        if robot_id in moved_robots:
            new_position = next(
                position for moved_robot_id, position in outcome.moved
                if moved_robot_id == robot_id
            )
            new_robot_state.position = new_position
            new_robot_state.battery_level = max(
                0.0, robot_state.battery_level - robot.battery_drain_per_unit_of_movement
            )
        elif robot_id in worked_robots:
            new_robot_state.battery_level = max(
                0.0, robot_state.battery_level - robot.battery_drain_per_unit_of_work_execution
            )
        else:
            new_robot_state.battery_level = max(
                0.0, robot_state.battery_level - robot.battery_drain_per_tick_idle
            )
        if robot_id in outcome.waypoints:
            new_robot_state.current_waypoint = outcome.waypoints[robot_id]
        new_robot_states[robot_id] = new_robot_state

    # --- Task states ----------------------------------------------------------
    new_task_states = dict(state.task_states)

    # Apply work progress
    work_ticks_by_task: dict[TaskId, int] = {}
    for robot_id, task_id in outcome.worked:
        work_ticks_by_task[task_id] = work_ticks_by_task.get(task_id, 0) + 1

    for task_id, ticks in work_ticks_by_task.items():
        task_state = new_task_states[task_id]
        assert isinstance(task_state, TaskState)
        new_task_state = copy.copy(task_state)
        if new_task_state.started_at is None:
            new_task_state.started_at = state.t_now
        new_task_state.work_done = Time(new_task_state.work_done.tick + ticks)
        new_task_states[task_id] = new_task_state

    # Apply rescue point discoveries to SearchTaskState
    for search_task_id, rescue_point_id in outcome.rescue_points_found:
        task_state = new_task_states[search_task_id]
        assert isinstance(task_state, SearchTaskState)
        new_task_state = SearchTaskState(
            task_id=task_state.task_id,
            status=task_state.status,
            completed_at=task_state.completed_at,
            rescue_found={**task_state.rescue_found, rescue_point_id: True},
        )
        new_task_states[search_task_id] = new_task_state

    # Mark completed tasks
    for task_id in outcome.tasks_completed:
        task_state = new_task_states[task_id]
        new_task_state = copy.copy(task_state)
        new_task_state.status = TaskStatus.DONE
        new_task_state.completed_at = new_time
        new_task_states[task_id] = new_task_state

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
        t_now=new_time,
    )
