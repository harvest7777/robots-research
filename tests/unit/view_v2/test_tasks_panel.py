"""Unit tests for simulation_view/v2/panels/tasks.py."""

from __future__ import annotations

from simulation.domain import (
    TaskId, TaskStatus, Environment, RescuePoint, Robot, RobotId, RobotState,
    SearchTask, SearchTaskState, WorkTask, SpatialConstraint, TaskState,
)
from simulation.engine_rewrite import SimulationState
from simulation.primitives import Position, Time

from simulation_view.terminal.panels.tasks import render_tasks



def _state(
    tasks: dict | None = None,
    task_states: dict | None = None,
    env_extra=None,
) -> SimulationState:
    env = Environment(width=10, height=10)
    if env_extra:
        env_extra(env)
    return SimulationState(
        environment=env,
        robots={RobotId(1): Robot(id=RobotId(1), capabilities=frozenset())},
        robot_states={RobotId(1): RobotState(robot_id=RobotId(1), position=Position(0, 0))},
        tasks=tasks or {},
        task_states=task_states or {},
        t_now=Time(0),
    )


def _work_task(
    task_id: int = 1,
    required: int = 10,
    work_done: int = 0,
    pos: Position = Position(5, 5),
) -> tuple[WorkTask, TaskState]:
    task = WorkTask(
        id=TaskId(task_id),
        priority=5,
        required_work_time=Time(required),
        spatial_constraint=SpatialConstraint(target=pos, max_distance=0),
    )
    ts = TaskState(task_id=TaskId(task_id), work_done=Time(work_done))
    return task, ts


def test_shows_tasks_header():
    lines = render_tasks(_state())
    assert lines[0] == "Tasks:"


def test_shows_task_label():
    task, ts = _work_task()
    lines = render_tasks(_state(tasks={task.id: task}, task_states={ts.task_id: ts}))
    assert any("[WK]" in l for l in lines)


def test_shows_task_priority():
    task, ts = _work_task()
    lines = render_tasks(_state(tasks={task.id: task}, task_states={ts.task_id: ts}))
    assert any("priority=5" in l for l in lines)


def test_shows_work_progress():
    task, ts = _work_task(required=10, work_done=3)
    lines = render_tasks(_state(tasks={task.id: task}, task_states={ts.task_id: ts}))
    assert any("progress=3/10" in l for l in lines)


def test_shows_not_started_symbol():
    task, ts = _work_task()
    lines = render_tasks(_state(tasks={task.id: task}, task_states={ts.task_id: ts}))
    assert any("○" in l for l in lines)


def test_shows_done_symbol():
    task, _ = _work_task()
    ts = TaskState(task_id=task.id, status=TaskStatus.DONE, completed_at=Time(5))
    lines = render_tasks(_state(tasks={task.id: task}, task_states={task.id: ts}))
    assert any("●" in l for l in lines)


def test_shows_in_progress_symbol():
    task, _ = _work_task()
    ts = TaskState(task_id=task.id, work_done=Time(2), started_at=Time(1))
    lines = render_tasks(_state(tasks={task.id: task}, task_states={task.id: ts}))
    assert any("◑" in l for l in lines)


def test_search_task_shows_found_progress():
    task = SearchTask(id=TaskId(1), priority=1)
    _rp_task = WorkTask(
        id=TaskId(2),
        priority=1,
        spatial_constraint=SpatialConstraint(target=Position(3, 3), max_distance=0),
    )
    rp = RescuePoint(
        id=TaskId(2),
        name="RP1",
        spatial_constraint=SpatialConstraint(target=Position(3, 3), max_distance=0),
        task=_rp_task,
        initial_task_state=TaskState(task_id=TaskId(2)),
    )

    def add_rp(env):
        env.add_rescue_point(rp)

    ts = SearchTaskState(task_id=TaskId(1), rescue_found=frozenset([TaskId(2)]))
    lines = render_tasks(
        _state(
            tasks={TaskId(1): task},
            task_states={TaskId(1): ts},
            env_extra=add_rp,
        )
    )
    assert any("found=1/1" in l for l in lines)


def test_task_without_state_skipped():
    task, _ = _work_task()
    # task_states is empty — task has no state yet
    lines = render_tasks(_state(tasks={task.id: task}, task_states={}))
    task_lines = [l for l in lines if "Task" in l and l.strip().startswith(("○", "●", "◑", "✗"))]
    assert len(task_lines) == 0
