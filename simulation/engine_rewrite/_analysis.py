"""
SimulationAnalysis

Pure value object derived from a simulation history (the sequence of
(SimulationState, StepOutcome) pairs produced by SimulationRunner.step()).

Contains no runner coupling — callers that accumulate history manually
can build this directly via from_history() without going through the runner.

Metrics
-------
total_ticks     : number of ticks elapsed (== final state's t_now)
makespan        : tick at which the last task completed; None if no tasks
                  ever completed
tasks_completed : number of distinct tasks that reached DONE status
tasks_failed    : number of distinct tasks that reached FAILED status
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.domain.base_task import TaskId, TaskStatus

from simulation.domain.simulation_state import SimulationState
from simulation.domain.step_outcome import StepOutcome


@dataclass(frozen=True)
class SimulationAnalysis:
    total_ticks: int
    makespan: int | None
    tasks_completed: int
    tasks_failed: int

    @classmethod
    def from_history(
        cls,
        history: list[tuple[SimulationState, StepOutcome]],
    ) -> SimulationAnalysis:
        if not history:
            return cls(total_ticks=0, makespan=None, tasks_completed=0, tasks_failed=0)

        final_state, _ = history[-1]
        total_ticks = final_state.t_now.tick

        completed_ids: set[TaskId] = set()
        for _, outcome in history:
            completed_ids.update(outcome.tasks_completed)

        failed_ids: set[TaskId] = {
            task_id
            for task_id, ts in final_state.task_states.items()
            if ts.status == TaskStatus.FAILED
        }

        makespan: int | None = None
        if completed_ids:
            completion_ticks = [
                ts.completed_at.tick
                for tid in completed_ids
                if (ts := final_state.task_states.get(tid)) is not None
                and ts.completed_at is not None
            ]
            if completion_ticks:
                makespan = max(completion_ticks)

        return cls(
            total_ticks=total_ticks,
            makespan=makespan,
            tasks_completed=len(completed_ids),
            tasks_failed=len(failed_ids),
        )
