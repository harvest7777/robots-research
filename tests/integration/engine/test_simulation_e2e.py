"""
End-to-end integration tests for Simulation.run().

Each test is prefixed with the scenario name it exercises so that when
additional scenarios are added, their expected behaviour can be asserted
independently.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scenario_loaders.load_simulation import load_simulation
from services.base_assignment_service import BaseAssignmentService
from simulation.algorithms.astar_pathfinding import astar_pathfind
from simulation.algorithms.simple_assignment import simple_assign
from simulation.domain.assignment import Assignment
from simulation.domain.task import TaskType
from simulation.domain.task_state import TaskStatus
from simulation.engine.simulation import Simulation
from simulation.primitives.time import Time

_SCENARIOS_DIR = Path(__file__).parent.parent.parent / "fixtures" / "scenarios"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _InMemoryAssignmentService(BaseAssignmentService):
    """Minimal in-memory assignment service for testing."""

    def __init__(self, assignments: list[Assignment] | None = None) -> None:
        self._assignments: list[Assignment] = assignments or []

    def get_assignments_for_time(self, time: Time) -> list[Assignment]:
        all_robot_ids = {rid for a in self._assignments for rid in a.robot_ids}
        seen: set[Assignment] = set()
        for robot_id in all_robot_ids:
            applicable = [
                a for a in self._assignments
                if robot_id in a.robot_ids and a.assign_at.tick <= time.tick
            ]
            if applicable:
                seen.add(max(applicable, key=lambda a: a.assign_at.tick))
        return list(seen)

    def set_assignments(self, assignments: list[Assignment]) -> None:
        self._assignments = list(assignments)

    def add_assignments(self, assignments: list[Assignment]) -> None:
        self._assignments.extend(assignments)


def _load_wired(scenario_name: str) -> Simulation:
    """Load a scenario by name, wire up assignments and pathfinding."""
    path = _SCENARIOS_DIR / f"{scenario_name}.json"
    sim = load_simulation(path)
    assignments = simple_assign(sim.tasks, sim.robots)
    sim.assignment_service = _InMemoryAssignmentService(assignments)
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
    result = sim.run(max_delta_time=100)
    assert result.completed is True
    assert result.tasks_succeeded == result.tasks_total


def test_basic_completion__run_returns_correct_makespan():
    sim = _load_wired("test_basic_completion")
    result = sim.run(max_delta_time=100)
    assert result.makespan is not None
    assert result.makespan > 0


def test_basic_completion__snapshots_recorded_each_tick():
    sim = _load_wired("test_basic_completion")
    result = sim.run(max_delta_time=100)
    # history includes tick 0 snapshot from __post_init__, plus one per step
    assert len(sim.history) == result.makespan + 1


def test_basic_completion__all_tasks_done_at_end():
    sim = _load_wired("test_basic_completion")
    sim.run(max_delta_time=100)
    non_idle_tasks = [t for t in sim.tasks if t.type != TaskType.IDLE]
    for task in non_idle_tasks:
        assert sim.task_states[task.id].status == TaskStatus.DONE


def test_basic_completion__idle_tasks_do_not_block_completion():
    """IDLE task present in scenario → run() still terminates when non-idle tasks complete."""
    sim = _load_wired("test_basic_completion")
    idle_tasks = [t for t in sim.tasks if t.type == TaskType.IDLE]
    assert len(idle_tasks) >= 1, "scenario must contain at least one IDLE task"
    result = sim.run(max_delta_time=100)
    assert result.completed is True


def test_basic_completion__on_tick_callback_called_each_tick():
    sim = _load_wired("test_basic_completion")
    call_count = 0

    def on_tick(snapshot):
        nonlocal call_count
        call_count += 1

    result = sim.run(max_delta_time=100, on_tick=on_tick)
    assert call_count == result.makespan


# ---------------------------------------------------------------------------
# test_time_budget_exceeded scenario
# ---------------------------------------------------------------------------

def test_time_budget_exceeded__returns_not_completed():
    sim = _load_wired("test_time_budget_exceeded")
    result = sim.run(max_delta_time=5)
    assert result.completed is False
    assert result.makespan is None
