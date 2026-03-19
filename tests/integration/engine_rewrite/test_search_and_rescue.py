from simulation.domain import RescuePoint

from scenarios_v2.search_and_rescue import run, RESCUE_POINT_ID, ROBOT_IDS


def test_rescue_point_is_discovered():
    _, outcomes, _ = run()
    assert any(isinstance(t, RescuePoint) for o in outcomes for t, _ in o.tasks_spawned)


def test_rescue_task_completes():
    _, outcomes, _ = run()
    assert any(RESCUE_POINT_ID in o.tasks_completed for o in outcomes)


def test_all_robots_converge_within_max_distance():
    # Derive the rescue point's location and detection radius from the final
    # simulation state rather than importing private scenario constants.
    state, _, _ = run()
    rp = state.environment.rescue_points[RESCUE_POINT_ID]
    target = rp.spatial_constraint.target
    max_dist = rp.spatial_constraint.max_distance
    for robot_id in ROBOT_IDS:
        pos = state.robot_states[robot_id].position
        assert pos.manhattan(target) <= max_dist


def test_analysis_counts_both_tasks_completed():
    _, _, runner = run()
    report = runner.report()
    # search task + rescue task
    assert report.tasks_completed == 2
    assert report.makespan is not None
