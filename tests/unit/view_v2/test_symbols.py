"""Unit tests for simulation_view/v2/symbols.py."""

from __future__ import annotations

from simulation.domain import TaskId, TaskStatus, SearchTask, SearchTaskState, WorkTask, TaskState
from simulation.primitives import Time

from simulation_view.terminal.symbols import (
    task_id_symbol,
    task_label,
    task_full_name,
    task_status_symbol,
)


# ---------------------------------------------------------------------------
# task_label
# ---------------------------------------------------------------------------


def test_task_label_search_task():
    task = SearchTask(id=TaskId(1), priority=1)
    assert task_label(task) == "SR"


def test_task_label_work_task():
    task = WorkTask(id=TaskId(1), priority=1)
    assert task_label(task) == "WK"


# ---------------------------------------------------------------------------
# task_full_name
# ---------------------------------------------------------------------------


def test_task_full_name_search_task():
    task = SearchTask(id=TaskId(1), priority=1)
    assert task_full_name(task) == "Search"


def test_task_full_name_work_task():
    task = WorkTask(id=TaskId(1), priority=1)
    assert task_full_name(task) == "Work"


# ---------------------------------------------------------------------------
# task_status_symbol
# ---------------------------------------------------------------------------


def test_task_status_symbol_done():
    state = TaskState(task_id=TaskId(1), status=TaskStatus.DONE, completed_at=Time(5))
    assert task_status_symbol(state) == "●"


def test_task_status_symbol_failed():
    state = TaskState(task_id=TaskId(1), status=TaskStatus.FAILED, completed_at=Time(5))
    assert task_status_symbol(state) == "✗"


def test_task_status_symbol_in_progress():
    state = TaskState(task_id=TaskId(1), started_at=Time(1))
    assert task_status_symbol(state) == "◑"


def test_task_status_symbol_not_started():
    state = TaskState(task_id=TaskId(1))
    assert task_status_symbol(state) == "○"


def test_task_status_symbol_search_task_not_started():
    state = SearchTaskState(task_id=TaskId(1))
    assert task_status_symbol(state) == "○"


# ---------------------------------------------------------------------------
# task_id_symbol
# ---------------------------------------------------------------------------


def test_task_id_symbol_single_digit():
    assert task_id_symbol(TaskId(1)) == "1"
    assert task_id_symbol(TaskId(9)) == "9"


def test_task_id_symbol_overflow():
    assert task_id_symbol(TaskId(10)) == "*"
    assert task_id_symbol(TaskId(99)) == "*"
