from simulation_models.assignment import Assignment
from simulation_models.robot_state import RobotId
from simulation_models.rescue_handler import RescueEffect, compute_rescue_effect
from simulation_models.rescue_point import RescuePoint, RescuePointId
from simulation_models.task import Task, TaskId, TaskType
from simulation_models.time import Time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _search_task(task_id: int) -> Task:
    return Task(id=TaskId(task_id), type=TaskType.SEARCH, priority=1, required_work_time=Time(1))


def _rescue_task(task_id: int) -> Task:
    return Task(id=TaskId(task_id), type=TaskType.RESCUE, priority=1, required_work_time=Time(1))


def _rp(rp_id: int, rescue_task_id: int) -> RescuePoint:
    from simulation_models.position import Position
    return RescuePoint(
        id=RescuePointId(rp_id),
        position=Position(0, 0),
        name=f"rp{rp_id}",
        rescue_task_id=TaskId(rescue_task_id),
    )


# ---------------------------------------------------------------------------
# rescue_found_updates
# ---------------------------------------------------------------------------

def test_rescue_found_updates_marks_rescue_point_as_found():
    rp = _rp(rp_id=1, rescue_task_id=10)
    search_task = _search_task(2)

    effect = compute_rescue_effect(
        rescue_point=rp,
        robot_to_task={RobotId(1): TaskId(2)},
        task_by_id={TaskId(2): search_task},
        t_now=Time(5),
    )

    assert effect.rescue_found_updates == {RescuePointId(1): True}


# ---------------------------------------------------------------------------
# new_assignment
# ---------------------------------------------------------------------------

def test_new_assignment_targets_rescue_task():
    rp = _rp(rp_id=1, rescue_task_id=10)
    search_task = _search_task(2)

    effect = compute_rescue_effect(
        rescue_point=rp,
        robot_to_task={RobotId(1): TaskId(2)},
        task_by_id={TaskId(2): search_task},
        t_now=Time(5),
    )

    assert effect.new_assignment.task_id == TaskId(10)


def test_new_assignment_includes_all_search_robots():
    rp = _rp(rp_id=1, rescue_task_id=10)
    search_task = _search_task(2)

    effect = compute_rescue_effect(
        rescue_point=rp,
        robot_to_task={RobotId(1): TaskId(2), RobotId(2): TaskId(2)},
        task_by_id={TaskId(2): search_task},
        t_now=Time(5),
    )

    assert effect.new_assignment.robot_ids == frozenset({RobotId(1), RobotId(2)})


def test_new_assignment_assign_at_matches_t_now():
    rp = _rp(rp_id=1, rescue_task_id=10)
    search_task = _search_task(2)

    effect = compute_rescue_effect(
        rescue_point=rp,
        robot_to_task={RobotId(1): TaskId(2)},
        task_by_id={TaskId(2): search_task},
        t_now=Time(7),
    )

    assert effect.new_assignment.assign_at == Time(7)


def test_new_assignment_excludes_non_search_robots():
    rp = _rp(rp_id=1, rescue_task_id=10)
    search_task = _search_task(2)
    rescue_task = _rescue_task(10)

    effect = compute_rescue_effect(
        rescue_point=rp,
        robot_to_task={RobotId(1): TaskId(2), RobotId(2): TaskId(10)},
        task_by_id={TaskId(2): search_task, TaskId(10): rescue_task},
        t_now=Time(5),
    )

    assert RobotId(1) in effect.new_assignment.robot_ids
    assert RobotId(2) not in effect.new_assignment.robot_ids


# ---------------------------------------------------------------------------
# tasks_to_mark_done
# ---------------------------------------------------------------------------

def test_tasks_to_mark_done_contains_all_search_task_ids():
    rp = _rp(rp_id=1, rescue_task_id=10)
    search_task_a = _search_task(2)
    search_task_b = _search_task(3)

    effect = compute_rescue_effect(
        rescue_point=rp,
        robot_to_task={RobotId(1): TaskId(2)},
        task_by_id={TaskId(2): search_task_a, TaskId(3): search_task_b},
        t_now=Time(5),
    )

    assert set(effect.tasks_to_mark_done) == {TaskId(2), TaskId(3)}


def test_tasks_to_mark_done_excludes_non_search_tasks():
    rp = _rp(rp_id=1, rescue_task_id=10)
    search_task = _search_task(2)
    rescue_task = _rescue_task(10)

    effect = compute_rescue_effect(
        rescue_point=rp,
        robot_to_task={RobotId(1): TaskId(2)},
        task_by_id={TaskId(2): search_task},
        t_now=Time(5),
    )

    assert TaskId(10) not in effect.tasks_to_mark_done


# ---------------------------------------------------------------------------
# waypoints_to_clear
# ---------------------------------------------------------------------------

def test_waypoints_to_clear_contains_all_search_robot_ids():
    rp = _rp(rp_id=1, rescue_task_id=10)
    search_task = _search_task(2)

    effect = compute_rescue_effect(
        rescue_point=rp,
        robot_to_task={RobotId(1): TaskId(2), RobotId(2): TaskId(2)},
        task_by_id={TaskId(2): search_task},
        t_now=Time(5),
    )

    assert set(effect.waypoints_to_clear) == {RobotId(1), RobotId(2)}


def test_waypoints_to_clear_excludes_non_search_robots():
    rp = _rp(rp_id=1, rescue_task_id=10)
    search_task = _search_task(2)
    rescue_task = _rescue_task(10)

    effect = compute_rescue_effect(
        rescue_point=rp,
        robot_to_task={RobotId(1): TaskId(2), RobotId(2): TaskId(10)},
        task_by_id={TaskId(2): search_task, TaskId(10): rescue_task},
        t_now=Time(5),
    )

    assert RobotId(1) in effect.waypoints_to_clear
    assert RobotId(2) not in effect.waypoints_to_clear


# ---------------------------------------------------------------------------
# No search robots
# ---------------------------------------------------------------------------

def test_no_search_robots_produces_empty_assignment_and_no_waypoints():
    rp = _rp(rp_id=1, rescue_task_id=10)
    rescue_task = _rescue_task(10)

    effect = compute_rescue_effect(
        rescue_point=rp,
        robot_to_task={RobotId(1): TaskId(10)},
        task_by_id={TaskId(10): rescue_task},
        t_now=Time(5),
    )

    assert effect.new_assignment.robot_ids == frozenset()
    assert effect.waypoints_to_clear == []
    assert effect.tasks_to_mark_done == []
