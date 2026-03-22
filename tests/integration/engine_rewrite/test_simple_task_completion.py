from tests.integration.fixtures.simple_task_completion import run, TASK_ID


def test_task_completes_before_max_ticks():
    _, outcomes, _ = run()
    assert any(TASK_ID in o.tasks_completed for o in outcomes)


def test_makespan_is_set():
    _, _, runner = run()
    report = runner.stop()
    assert report.makespan is not None



def test_analysis_counts_one_completed_task():
    _, _, runner = run()
    report = runner.stop()
    assert report.tasks_completed == 1
    assert report.tasks_failed == 0
