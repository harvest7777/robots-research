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

# TODO de duplicate this by just implmeenting it within the services/
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
# test basic mutations to Simulation fields
# ---------------------------------------------------------------------------

def test_step_increments_time():
    path = _SCENARIOS_DIR / "test_basic_completion"
    sim = _load_wired(path)

    old_time = sim.t_now
    sim._step()
    assert old_time.tick == sim.t_now.tick - Time(1).tick

def test_step_increments_delta_time():
    path =  "test_basic_completion"
    sim = _load_wired(path)

    assert sim.dt == Time(0)

    sim._step()
    assert sim.dt == Time(1)

    sim._step()

    assert sim.dt == Time(2)

def test_multiple_robots_working_on_one_task_finishes_faster_than_one_robot_working_on_one_task():
    path = "test_two_robots_same_task"
    two_robot_sim = _load_wired(path)
    LONG_TIME = Time(1000)

    two_robot_result = two_robot_sim.run(LONG_TIME)

    path =  "test_one_robot_same_task"
    one_robot_sim = _load_wired(path)
    one_robot_result = one_robot_sim.run(LONG_TIME)

    assert two_robot_result.makespan < one_robot_result.makespan

def test_dependency_blocks_work():
    path = "test_dependent_tasks"
    two_robot_sim = _load_wired(path)
    two_robot_sim._step()
    assert two_robot_sim.task_states[1].work_done==Time(1)
    assert two_robot_sim.task_states[1].started_at == Time(1)
    assert two_robot_sim.task_states[2].work_done==Time(0)
    assert two_robot_sim.task_states[2].started_at == None

def test_dependency_causes_higher_makespan_during_sequential_task_execution():
    path = "test_dependent_tasks"
    two_robot_sim = _load_wired(path)
    LONG_TIME = Time(1000)
    TOTAL_TASK_TIME = two_robot_sim._task_by_id[1].required_work_time + two_robot_sim._task_by_id[2].required_work_time
    result = two_robot_sim.run(LONG_TIME)

    assert result.makespan == TOTAL_TASK_TIME
