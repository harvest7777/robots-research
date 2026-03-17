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

import dataclasses

from simulation.domain.base_task import TaskId, TaskStatus
from simulation.domain.robot_state import RobotId, RobotState
from simulation.domain.search_task import SearchTaskState
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
    moved_positions: dict[RobotId, object] = dict(outcome.moved)

    # --- Robot states ---------------------------------------------------------
    new_robot_states: dict[RobotId, RobotState] = {}
    for robot_id, robot_state in state.robot_states.items():
        robot = state.robots[robot_id]
        if robot_id in moved_robots:
            new_position = moved_positions[robot_id]
            new_battery = max(0.0, robot_state.battery_level - robot.battery_drain_per_unit_of_movement)
        elif robot_id in worked_robots:
            new_position = robot_state.position
            new_battery = max(0.0, robot_state.battery_level - robot.battery_drain_per_unit_of_work_execution)
        else:
            new_position = robot_state.position
            new_battery = max(0.0, robot_state.battery_level - robot.battery_drain_per_tick_idle)
        new_robot_states[robot_id] = RobotState(
            robot_id=robot_id,
            position=new_position,
            battery_level=new_battery,
            current_waypoint=outcome.waypoints.get(robot_id, robot_state.current_waypoint),
        )

    # --- Task states ----------------------------------------------------------
    new_task_states = dict(state.task_states)

    # Apply work progress — lazy-init TaskState on first work tick
    work_ticks_by_task: dict[TaskId, int] = {}
    for _, task_id in outcome.worked:
        work_ticks_by_task[task_id] = work_ticks_by_task.get(task_id, 0) + 1

    for task_id, ticks in work_ticks_by_task.items():
        existing = new_task_states.get(task_id)
        prev_work = existing.work_done.tick if isinstance(existing, TaskState) else 0
        started_at = existing.started_at if isinstance(existing, TaskState) and existing.started_at is not None else state.t_now
        new_task_states[task_id] = TaskState(
            task_id=task_id,
            work_done=Time(prev_work + ticks),
            started_at=started_at,
        )

    # Apply rescue point discoveries to SearchTaskState
    for rp_id in outcome.rescue_points_found:
        for search_task_id, task_state in new_task_states.items():
            if isinstance(task_state, SearchTaskState):
                new_task_states[search_task_id] = dataclasses.replace(
                    task_state,
                    rescue_found=task_state.rescue_found | frozenset({rp_id}),
                )
                break

    # Mark completed tasks
    for task_id in outcome.tasks_completed:
        task_state = new_task_states[task_id]
        new_task_states[task_id] = dataclasses.replace(
            task_state,
            status=TaskStatus.DONE,
            completed_at=new_time,
        )

    return SimulationState(
        environment=state.environment,
        robots=state.robots,
        robot_states=new_robot_states,
        tasks=state.tasks,
        task_states=new_task_states,
        t_now=new_time,
        assignments=state.assignments,
    )
