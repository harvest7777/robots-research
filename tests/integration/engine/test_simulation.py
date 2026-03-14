"""
Integration tests for the simulation engine.

Tests are grouped by scenario. Each group exercises a distinct behavioral
contract of Simulation.run() or Simulation._step().
"""

from __future__ import annotations

from pathlib import Path

from scenario_loaders.load_simulation import load_simulation
from services.in_memory_assignment_service import InMemoryAssignmentService
from simulation.algorithms.astar_pathfinding import astar_pathfind
from simulation.algorithms.simple_assignment import simple_assign
from simulation.domain.task import TaskId, TaskType, Task
from simulation.domain.task_state import TaskStatus
from simulation.engine.simulation import Simulation
from simulation.primitives.time import Time

_SCENARIOS_DIR = Path(__file__).parent.parent.parent / "fixtures" / "scenarios"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_wired(scenario_name: str) -> Simulation:
    """Load a scenario by name, wire up assignments and pathfinding."""
    path = _SCENARIOS_DIR / f"{scenario_name}.json"
    sim = load_simulation(path)
    assignments = simple_assign(sim.tasks, sim.robots)
    sim.assignment_service = InMemoryAssignmentService(assignments)
    sim.pathfinding_algorithm = astar_pathfind
    return sim


# ---------------------------------------------------------------------------
# test_basic_completion scenario
# ---------------------------------------------------------------------------

def test_basic_completion__loads_scenario_from_json():
    path = _SCENARIOS_DIR / "test_basic_completion.json"
    sim = load_simulation(path)
    assert isinstance(sim, Simulation)


def test_basic_completion__run_completes_all_tasks():
    sim = _load_wired("test_basic_completion")
    result = sim.run(max_delta_time=Time(100))
    assert result.completed is True
    assert result.tasks_succeeded == result.tasks_total


def test_basic_completion__run_returns_correct_makespan():
    sim = _load_wired("test_basic_completion")
    result = sim.run(max_delta_time=Time(100))
    assert result.makespan is not None
    assert result.makespan > Time(0)


def test_basic_completion__snapshots_recorded_each_tick():
    sim = _load_wired("test_basic_completion")
    result = sim.run(max_delta_time=Time(100))
    # history includes tick 0 snapshot from __post_init__, plus one per step
    assert len(sim.history) == result.makespan.tick + 1


def test_basic_completion__all_tasks_done_at_end():
    sim = _load_wired("test_basic_completion")
    sim.run(max_delta_time=Time(100))
    non_idle_tasks = [t for t in sim.tasks if not (isinstance(t, Task) and t.type == TaskType.IDLE)]
    for task in non_idle_tasks:
        assert sim.task_states[task.id].status == TaskStatus.DONE


def test_basic_completion__idle_tasks_do_not_block_completion():
    """IDLE task present → run() still terminates when non-idle tasks complete."""
    sim = _load_wired("test_basic_completion")
    idle_tasks = [t for t in sim.tasks if t.type == TaskType.IDLE]
    assert len(idle_tasks) >= 1, "scenario must contain at least one IDLE task"
    result = sim.run(max_delta_time=Time(100))
    assert result.completed is True


def test_basic_completion__on_tick_callback_called_each_tick():
    sim = _load_wired("test_basic_completion")
    call_count = 0

    def on_tick(snapshot):
        nonlocal call_count
        call_count += 1

    result = sim.run(max_delta_time=Time(100), on_tick=on_tick)
    assert call_count == result.makespan.tick


# ---------------------------------------------------------------------------
# test_time_budget_exceeded scenario
# ---------------------------------------------------------------------------

def test_time_budget_exceeded__returns_not_completed():
    sim = _load_wired("test_time_budget_exceeded")
    result = sim.run(max_delta_time=Time(5))
    assert result.completed is False
    assert result.makespan is None


# ---------------------------------------------------------------------------
# test_maze_completion scenario
#
# 15x10 grid with two vertical obstacle columns that force robots to take
# an S-shaped detour. The only path through col 5 is at row 9; the only
# path through col 10 is at row 0.
# Robot 1 starts at (0,0) → task at (14,0)
# Robot 2 starts at (0,9) → task at (14,9)
# ---------------------------------------------------------------------------

def test_maze_completion__loads_scenario_from_json():
    path = _SCENARIOS_DIR / "test_maze_completion.json"
    sim = load_simulation(path)
    assert isinstance(sim, Simulation)


def test_maze_completion__both_tasks_complete_despite_obstacles():
    sim = _load_wired("test_maze_completion")
    result = sim.run(max_delta_time=Time(150))
    assert result.completed is True
    assert result.tasks_succeeded == result.tasks_total


# ---------------------------------------------------------------------------
# test_no_robot_collisions scenario
#
# 20x20 open grid with 10 robots: 5 moving horizontally (west→east) and
# 5 moving vertically (north→south). Their paths cross at multiple cells,
# exercising the collision resolver. The snapshot history is inspected at
# every tick to verify that no two robots ever share the same cell.
# ---------------------------------------------------------------------------

def test_no_robot_collisions__loads_scenario_from_json():
    path = _SCENARIOS_DIR / "test_no_robot_collisions.json"
    sim = load_simulation(path)
    assert isinstance(sim, Simulation)


def test_no_robot_collisions__all_tasks_complete():
    sim = _load_wired("test_no_robot_collisions")
    result = sim.run(max_delta_time=Time(500))
    assert result.completed is True
    assert result.tasks_succeeded == result.tasks_total


def test_no_robot_collisions__robots_never_share_a_cell():
    sim = _load_wired("test_no_robot_collisions")
    sim.run(max_delta_time=Time(500))

    for t, snapshot in sim.history.items():
        positions = [state.position for state in snapshot.robot_states.values()]
        assert len(positions) == len(set(positions)), (
            f"two robots occupy the same cell at tick {t.tick}: "
            f"{[p for p in positions if positions.count(p) > 1]}"
        )


# ---------------------------------------------------------------------------
# Multi-robot throughput
#
# Two robots on the same task should finish it faster than one robot alone.
# ---------------------------------------------------------------------------

def test_two_robots_on_same_task_finish_faster_than_one():
    two_robot_sim = _load_wired("test_two_robots_same_task")
    two_robot_result = two_robot_sim.run(max_delta_time=Time(1000))

    one_robot_sim = _load_wired("test_one_robot_same_task")
    one_robot_result = one_robot_sim.run(max_delta_time=Time(1000))

    assert two_robot_result.makespan < one_robot_result.makespan


# ---------------------------------------------------------------------------
# test_dependent_tasks scenario
#
# Task 2 declares task 1 as a dependency. Robot 2 starts adjacent to task 2
# but must wait until task 1 is DONE before any work is credited.
# ---------------------------------------------------------------------------

def test_dependent_tasks__task_b_does_not_start_before_task_a_completes():
    sim = _load_wired("test_dependent_tasks")
    sim.run(max_delta_time=Time(200))

    a_state = sim.task_states[TaskId(1)]
    b_state = sim.task_states[TaskId(2)]

    assert a_state.status == TaskStatus.DONE
    assert b_state.status == TaskStatus.DONE
    assert b_state.started_at >= a_state.completed_at


# ---------------------------------------------------------------------------
# test_battery_depletion scenario
#
# Robot starts with battery_level=0.001 at the task location.
# DRAIN_WORK_PER_TICK=0.002, so the robot contributes exactly one tick of
# work before its battery drops to ≤0. With required_work_time=5, the task
# can never complete.
# ---------------------------------------------------------------------------

def test_battery_depletion__task_stalls_when_robot_runs_out():
    sim = _load_wired("test_battery_depletion")
    result = sim.run(max_delta_time=Time(50))
    assert result.completed is False
    assert sim.task_states[TaskId(1)].status != TaskStatus.DONE


# ---------------------------------------------------------------------------
# test_task_deadline scenario
#
# Task has deadline=0. After the first _step(), t_now=1 > 0, so the task
# is immediately past its deadline and no work is ever applied.
# ---------------------------------------------------------------------------

def test_task_deadline__task_never_progresses_past_deadline():
    sim = _load_wired("test_task_deadline")
    result = sim.run(max_delta_time=Time(50))
    assert result.completed is False
    assert sim.task_states[TaskId(1)].status != TaskStatus.DONE
