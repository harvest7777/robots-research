from simulation.engine_rewrite import IgnoreReason

from scenarios_v2.battery_drain import run, TASK_ID


def test_task_does_not_complete():
    _, outcomes, _ = run()
    assert not any(TASK_ID in o.tasks_completed for o in outcomes)


def test_no_battery_fires():
    _, outcomes, _ = run()
    assert any(
        reason == IgnoreReason.NO_BATTERY
        for o in outcomes
        for _, reason in o.assignments_ignored
    )


def test_analysis_shows_no_completions():
    _, _, runner = run()
    report = runner.stop()
    assert report.tasks_completed == 0
    assert report.makespan is None
