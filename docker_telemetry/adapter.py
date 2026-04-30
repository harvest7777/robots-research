from simulation.domain.robot_state import RobotId
from simulation.domain.simulation_state import SimulationState
from simulation.domain.step_outcome import StepOutcome
from simulation.domain.task import WorkTask
from docker_telemetry.telemetry import RobotAction, RobotTelemetry


def build_telemetry(
    robot_id: RobotId,
    state: SimulationState,
    outcome: StepOutcome,
) -> RobotTelemetry:
    robot_state = state.robot_states[robot_id]

    moved_ids  = {r for r, _ in outcome.moved}
    worked_ids = {r for r, _ in outcome.worked}
    if robot_id in outcome.robots_stuck:
        action = RobotAction.STUCK
    elif robot_id in worked_ids:
        action = RobotAction.WORKED
    elif robot_id in moved_ids:
        action = RobotAction.MOVED
    else:
        action = RobotAction.IDLE

    assigned_task_ids = tuple(
        a.task_id for a in state.assignments if a.robot_id == robot_id
    )

    task_capabilities = frozenset(
        cap
        for task_id in assigned_task_ids
        if (task := state.tasks.get(task_id)) is not None
        for cap in task.required_capabilities
    )

    task_complexity: int | None = None
    deadline_delta_ticks: int | None = None
    for task_id in assigned_task_ids:
        task = state.tasks.get(task_id)
        if isinstance(task, WorkTask):
            task_complexity = task.required_work_time.tick
            if task.deadline is not None:
                deadline_delta_ticks = task.deadline.tick - state.t_now.tick
            break

    ignore_reasons = tuple(
        reason
        for assignment, reason in outcome.assignments_ignored
        if assignment.robot_id == robot_id
    )

    return RobotTelemetry(
        tick=state.t_now,
        robot_id=robot_id,
        position=robot_state.position,
        battery_level=robot_state.battery_level,
        current_waypoint=robot_state.current_waypoint,
        action=action,
        assigned_task_ids=assigned_task_ids,
        task_capabilities=task_capabilities,
        task_complexity=task_complexity,
        deadline_delta_ticks=deadline_delta_ticks,
        ignore_reasons=ignore_reasons,
    )
