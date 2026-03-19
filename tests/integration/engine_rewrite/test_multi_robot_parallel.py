from scenarios_v2.multi_robot_parallel import run, TASK_IDS


def test_all_tasks_complete_before_max_ticks():
    _, outcomes, _ = run()
    completed = {tid for o in outcomes for tid in o.tasks_completed}
    assert completed >= set(TASK_IDS)


def test_makespan_is_set():
    _, _, runner = run()
    report = runner.stop()
    assert report.makespan is not None



def test_analysis_counts_all_completed_tasks():
    _, _, runner = run()
    report = runner.stop()
    assert report.tasks_completed == len(TASK_IDS)
    assert report.tasks_failed == 0
