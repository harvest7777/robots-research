from simulation.domain import TaskId, WorkTask, SpatialConstraint
from simulation.primitives import Position, Time
from simulation.engine_rewrite.services import InMemoryTaskRegistry


def _task(tid: int, x: int = 0, y: int = 0) -> WorkTask:
    return WorkTask(
        id=TaskId(tid),
        priority=5,
        required_work_time=Time(10),
        spatial_constraint=SpatialConstraint(target=Position(x, y)),
    )


# ---------------------------------------------------------------------------
# add / all
# ---------------------------------------------------------------------------

def test_empty_registry_returns_no_tasks():
    registry = InMemoryTaskRegistry()
    assert registry.all() == []


def test_add_single_task_appears_in_all():
    registry = InMemoryTaskRegistry()
    task = _task(1)
    registry.add(task)
    assert registry.all() == [task]


def test_add_multiple_tasks_all_appear():
    registry = InMemoryTaskRegistry()
    t1, t2, t3 = _task(1), _task(2), _task(3)
    registry.add(t1)
    registry.add(t2)
    registry.add(t3)
    assert set(registry.all()) == {t1, t2, t3}


def test_adding_task_with_same_id_overwrites():
    registry = InMemoryTaskRegistry()
    original = _task(1, x=0, y=0)
    replacement = _task(1, x=9, y=9)
    registry.add(original)
    registry.add(replacement)
    assert registry.all() == [replacement]


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

def test_get_returns_task_by_id():
    registry = InMemoryTaskRegistry()
    task = _task(42)
    registry.add(task)
    assert registry.get(TaskId(42)) == task


def test_get_returns_none_for_missing_id():
    registry = InMemoryTaskRegistry()
    assert registry.get(TaskId(99)) is None


def test_get_does_not_affect_other_tasks():
    registry = InMemoryTaskRegistry()
    registry.add(_task(1))
    registry.add(_task(2))
    registry.get(TaskId(1))
    assert len(registry.all()) == 2


# ---------------------------------------------------------------------------
# constructor pre-load
# ---------------------------------------------------------------------------

def test_constructor_accepts_initial_tasks():
    t1, t2 = _task(1), _task(2)
    registry = InMemoryTaskRegistry(tasks=[t1, t2])
    assert set(registry.all()) == {t1, t2}


def test_constructor_with_no_args_is_empty():
    assert InMemoryTaskRegistry().all() == []
