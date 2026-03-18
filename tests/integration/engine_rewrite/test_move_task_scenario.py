from scenarios_v2.move_task import run, MOVE_TASK_ID


def test_move_task_completes_before_max_ticks():
    _, outcomes, _ = run()
    assert any(MOVE_TASK_ID in o.tasks_completed for o in outcomes)


def test_move_task_completes_with_tasks_moved_entries():
    _, outcomes, _ = run()
    assert any(len(o.tasks_moved) > 0 for o in outcomes)
