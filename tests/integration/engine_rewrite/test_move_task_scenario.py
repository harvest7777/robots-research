from simulation.domain.move_task import MoveTask, MoveTaskState

from scenarios_v2.move_task import run, MOVE_TASK_ID


def test_move_task_completes_before_max_ticks():
    _, outcomes, _ = run()
    assert any(MOVE_TASK_ID in o.tasks_completed for o in outcomes)


def test_move_task_ends_at_destination():
    state, _, _ = run()
    task = state.tasks[MOVE_TASK_ID]
    task_state = state.task_states[MOVE_TASK_ID]
    assert isinstance(task, MoveTask)
    assert isinstance(task_state, MoveTaskState)
    assert task_state.current_position == task.destination
