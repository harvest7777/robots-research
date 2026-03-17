from scenarios_v2.collaborative_task import run, TASK_ID, TASK_WORK_TIME


def test_task_completes_with_two_robots():
    _, outcomes, _ = run(num_robots=2)
    assert any(TASK_ID in o.tasks_completed for o in outcomes)


def test_two_robots_finish_faster_than_one():
    _, _, solo_runner = run(num_robots=1)
    _, _, duo_runner = run(num_robots=2)
    solo_makespan = solo_runner.report().makespan
    duo_makespan = duo_runner.report().makespan
    assert duo_makespan < solo_makespan


def test_two_robots_halve_the_makespan():
    _, _, runner = run(num_robots=2)
    report = runner.report()
    assert report.makespan == TASK_WORK_TIME // 2
