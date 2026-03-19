"""
Integration tests for the search_and_rescue_move scenario.

Key behaviour under test:
- A rescue point with max_distance=1 is discovered when the search robot
  is within 1 Manhattan unit — the robot does NOT step onto the exact
  rescue point cell.
- After discovery, all robots are assigned to the MoveTask and carry the
  casualty to the extraction zone.
"""

from simulation.domain import RobotId
from simulation.domain.move_task import MoveTask, MoveTaskState

from scenarios_v2.search_and_rescue_move import (
    build,
    run,
    MOVE_TASK_ID,
    RESCUE_POINT_ID,
    ROBOT_IDS,
)


def test_casualty_discovered_on_tick_1():
    """Proximity lock fires immediately — Robot 1 starts adjacent and
    discovery must happen on the very first tick."""
    runner, _ = build()
    _, outcome = runner.step()
    assert outcome.rescue_points_found


def test_searcher_does_not_step_onto_rescue_point():
    """With max_distance=1 the robot stops 1 step away from the rescue point.
    It must NOT move onto the exact casualty cell to trigger discovery."""
    runner, _ = build()
    state, outcome = runner.step()

    assert RESCUE_POINT_ID in {t.id for t, _ in outcome.tasks_spawned}, \
        "discovery did not fire on tick 1"

    # Derive casualty position from the discovered rescue point task itself.
    casualty_pos = next(
        t for t, _ in outcome.tasks_spawned if t.id == RESCUE_POINT_ID
    ).spatial_constraint.target

    robot1_pos = state.robot_states[RobotId(1)].position
    assert robot1_pos != casualty_pos, \
        f"Robot 1 stepped onto the rescue point cell {casualty_pos}"
    assert robot1_pos.manhattan(casualty_pos) <= 1, \
        f"Robot 1 ended up farther than max_distance=1 from casualty"


def test_move_task_completes():
    """End-to-end: after discovery the carriers form up and deliver the
    casualty to the extraction zone."""
    _, outcomes, _ = run()
    assert any(MOVE_TASK_ID in o.tasks_completed for o in outcomes)


def test_casualty_reaches_extraction_zone():
    """The MoveTask's final position must equal its destination."""
    state, _, _ = run()
    move_task = state.tasks[MOVE_TASK_ID]
    move_state = state.task_states[MOVE_TASK_ID]
    assert isinstance(move_task, MoveTask)
    assert isinstance(move_state, MoveTaskState)
    assert move_state.current_position == move_task.destination


def test_all_robots_reach_casualty_area():
    """All robots must end within 1 step of the final casualty position
    (they form the extraction formation)."""
    state, _, _ = run()
    final_task_pos = state.task_states[MOVE_TASK_ID].current_position  # type: ignore[union-attr]
    for robot_id in ROBOT_IDS:
        pos = state.robot_states[robot_id].position
        assert pos.manhattan(final_task_pos) <= 1, \
            f"Robot {robot_id} at {pos} is not adjacent to final casualty pos {final_task_pos}"
