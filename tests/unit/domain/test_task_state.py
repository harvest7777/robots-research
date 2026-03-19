from simulation.domain import TaskId, TaskState, TaskStatus, apply_work, mark_done, mark_failed
from simulation.primitives import Time


def _state(task_id: int = 1) -> TaskState:
    return TaskState(task_id=TaskId(task_id))


def _time(tick: int) -> Time:
    return Time(tick)


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

def test_initial_state_is_not_terminal():
    state = _state()
    assert state.status is None
    assert state.started_at is None
    assert state.work_done == Time(0)


# ---------------------------------------------------------------------------
# apply_work
# ---------------------------------------------------------------------------

def test_apply_work_sets_started_at():
    state = _state()
    apply_work(state, required_work_time=_time(10), dt=_time(1), t_now=_time(5))
    assert state.started_at == _time(5)
    assert state.status is None  # not terminal yet


def test_apply_work_accumulates_correctly():
    state = _state()
    apply_work(state, required_work_time=_time(10), dt=_time(3), t_now=_time(1))
    apply_work(state, required_work_time=_time(10), dt=_time(3), t_now=_time(2))
    assert state.work_done == Time(6)
    assert state.status is None


def test_apply_work_completes_task():
    state = _state()
    apply_work(state, required_work_time=_time(3), dt=_time(3), t_now=_time(7))
    assert state.status == TaskStatus.DONE
    assert state.completed_at == _time(7)


def test_apply_work_on_done_is_noop():
    state = _state()
    mark_done(state, _time(2))
    before = TaskState(
        task_id=state.task_id,
        status=state.status,
        work_done=state.work_done,
        started_at=state.started_at,
        completed_at=state.completed_at,
    )
    apply_work(state, required_work_time=_time(10), dt=_time(1), t_now=_time(3))
    assert state.status == before.status
    assert state.work_done == before.work_done
    assert state.completed_at == before.completed_at


def test_apply_work_on_failed_is_noop():
    state = _state()
    mark_failed(state, _time(2))
    before_work_done = state.work_done
    before_completed_at = state.completed_at
    apply_work(state, required_work_time=_time(10), dt=_time(1), t_now=_time(3))
    assert state.status == TaskStatus.FAILED
    assert state.work_done == before_work_done
    assert state.completed_at == before_completed_at


def test_started_at_not_overwritten():
    state = _state()
    apply_work(state, required_work_time=_time(10), dt=_time(1), t_now=_time(5))
    apply_work(state, required_work_time=_time(10), dt=_time(1), t_now=_time(6))
    assert state.started_at == _time(5)


# ---------------------------------------------------------------------------
# mark_done
# ---------------------------------------------------------------------------

def test_mark_done_sets_status_and_time():
    state = _state()
    mark_done(state, _time(42))
    assert state.status == TaskStatus.DONE
    assert state.completed_at == _time(42)


def test_mark_done_without_prior_work():
    # Rescue handler marks SEARCH tasks done regardless of work accumulated.
    state = _state()
    assert state.work_done == Time(0)
    mark_done(state, _time(10))
    assert state.status == TaskStatus.DONE
    assert state.work_done == Time(0)


# ---------------------------------------------------------------------------
# mark_failed
# ---------------------------------------------------------------------------

def test_mark_failed_sets_status_and_time():
    state = _state()
    mark_failed(state, _time(99))
    assert state.status == TaskStatus.FAILED
    assert state.completed_at == _time(99)
