import pytest
from simulation.domain.robot import _DRAIN_IDLE_PER_TICK, _DRAIN_MOVE_PER_TICK, _DRAIN_WORK_PER_TICK, idle_robot, move_robot, work_robot
from simulation.domain.robot_state import RobotId, RobotState
from simulation.primitives.position import Position


def _state(battery: float = 1.0) -> RobotState:
    return RobotState(robot_id=RobotId(1), position=Position(0, 0), battery_level=battery)


# ---------------------------------------------------------------------------
# Battery drain rates
# ---------------------------------------------------------------------------

def test_step_to_drains_move_battery():
    state = _state()
    move_robot(state, Position(1, 0))
    assert state.battery_level == pytest.approx(1.0 - _DRAIN_MOVE_PER_TICK)


def test_work_drains_work_battery():
    state = _state()
    work_robot(state)
    assert state.battery_level == pytest.approx(1.0 - _DRAIN_WORK_PER_TICK)


def test_idle_drains_idle_battery():
    state = _state()
    idle_robot(state)
    assert state.battery_level == pytest.approx(1.0 - _DRAIN_IDLE_PER_TICK)


def test_battery_goes_below_zero_when_depleted():
    # RobotState has no floor — battery goes negative. This is intentional
    # (the engine decides what to do with a drained robot, not robot.py).
    state = _state(battery=0.0)
    work_robot(state)
    assert state.battery_level < 0.0


def test_multi_tick_accumulation():
    state = _state()
    move_robot(state, Position(1, 0))
    move_robot(state, Position(2, 0))
    move_robot(state, Position(3, 0))
    assert state.battery_level == pytest.approx(1.0 - 3 * _DRAIN_MOVE_PER_TICK)
