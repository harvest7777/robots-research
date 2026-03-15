"""Unit tests for StepOutcome and IgnoreReason."""

from simulation.domain.base_task import TaskId
from simulation.domain.robot_state import RobotId
from simulation.primitives.position import Position
from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.step_outcome import IgnoreReason, StepOutcome


def test_step_outcome_defaults_are_empty():
    outcome = StepOutcome()
    assert outcome.moved == []
    assert outcome.worked == []
    assert outcome.tasks_completed == []
    assert outcome.tasks_spawned == []
    assert outcome.assignments_ignored == []
    assert outcome.rescue_points_found == []


def test_ignore_reason_values_are_distinct():
    reasons = list(IgnoreReason)
    assert len(reasons) == len(set(r.value for r in reasons))


def test_assignment_is_hashable():
    a = Assignment(task_id=TaskId(1), robot_id=RobotId(2))
    b = Assignment(task_id=TaskId(1), robot_id=RobotId(2))
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1
