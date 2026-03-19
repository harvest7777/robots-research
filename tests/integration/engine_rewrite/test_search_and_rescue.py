from simulation.domain import RescuePoint

from scenarios_v2.search_and_rescue import (
    run,
    RESCUE_POINT_ID,
    ROBOT_IDS,
    _RESCUE_POSITION,
    _RESCUE_MAX_DIST,
)


def test_rescue_point_is_discovered_on_tick_1():
    _, outcomes, _ = run()
    assert any(isinstance(t, RescuePoint) for t in outcomes[0].tasks_spawned)


def test_rescue_task_completes():
    _, outcomes, _ = run()
    assert any(RESCUE_POINT_ID in o.tasks_completed for o in outcomes)


def test_all_robots_converge_within_max_distance():
    state, _, _ = run()
    for robot_id in ROBOT_IDS:
        pos = state.robot_states[robot_id].position
        assert pos.manhattan(_RESCUE_POSITION) <= _RESCUE_MAX_DIST


def test_analysis_counts_both_tasks_completed():
    _, _, runner = run()
    report = runner.report()
    # search task + rescue task
    assert report.tasks_completed == 2
    assert report.makespan is not None
