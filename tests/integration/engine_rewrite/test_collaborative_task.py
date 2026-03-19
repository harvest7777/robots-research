from scenarios_v2.collaborative_task import run, TASK_ID, TASK_WORK_TIME


def test_task_completes_with_two_robots():
    _, outcomes, _ = run(num_robots=2)
    assert any(TASK_ID in o.tasks_completed for o in outcomes)


def test_two_robots_finish_faster_than_one():
    _, _, solo_runner = run(num_robots=1)
    _, _, duo_runner = run(num_robots=2)
    solo_makespan = solo_runner.stop().makespan
    duo_makespan = duo_runner.stop().makespan
    assert duo_makespan < solo_makespan


