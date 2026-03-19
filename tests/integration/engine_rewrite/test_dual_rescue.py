from scenarios_v2.dual_rescue import (
    run,
    RESCUE_POINT_A_ID,
    RESCUE_POINT_B_ID,
    MOVE_TASK_A_ID,
    MOVE_TASK_B_ID,
)


def test_both_casualties_discovered():
    _, outcomes, _ = run()
    found = {rp for o in outcomes for rp in o.rescue_points_found}
    assert RESCUE_POINT_A_ID in found
    assert RESCUE_POINT_B_ID in found


def test_both_move_tasks_complete():
    _, outcomes, _ = run()
    completed = {t for o in outcomes for t in o.tasks_completed}
    assert MOVE_TASK_A_ID in completed
    assert MOVE_TASK_B_ID in completed


def test_casualty_a_reaches_extraction_zone():
    state, _, _ = run()
    move_a = state.task_states[MOVE_TASK_A_ID]
    dest = state.environment.rescue_points[RESCUE_POINT_A_ID]
    # Destination is stored on the MoveTask itself; retrieve via the task registry.
    task_a = state.tasks[MOVE_TASK_A_ID]
    assert move_a.current_position == task_a.destination


def test_casualty_b_reaches_extraction_zone():
    state, _, _ = run()
    move_b = state.task_states[MOVE_TASK_B_ID]
    task_b = state.tasks[MOVE_TASK_B_ID]
    assert move_b.current_position == task_b.destination


def test_analysis_counts_completed_tasks():
    _, _, runner = run()
    report = runner.stop()
    # search task + move A + move B = 3
    # (rescue point WorkTasks are never assigned workers — robots go straight to MoveTasks)
    assert report.tasks_completed == 3
    assert report.tasks_failed == 0
    assert report.makespan is not None
