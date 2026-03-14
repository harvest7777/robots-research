"""
Search Phase Handler

Pure function for computing the effect of one or more rescue point discoveries
in a single tick. Accepts a batch of (robot_id, rescue_point, search_task_id)
tuples so that simultaneous multi-rescue discoveries are handled atomically.

Returns a SearchEffect describing all state changes required — the caller
(Simulation._step) is responsible for applying them. No state is mutated here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.domain.assignment import Assignment
from simulation.domain.base_task import BaseTask, TaskId, mark_done
from simulation.domain.rescue_point import RescuePoint, RescuePointId
from simulation.domain.robot_state import RobotId
from simulation.domain.search_task import SearchTask, SearchTaskState
from simulation.primitives.time import Time


@dataclass
class SearchEffect:
    """All state changes triggered by one or more rescue point discoveries.

    Attributes:
        rescue_found_updates:       Per-search-task updates to rescue_found.
                                    Keyed by search_task_id, value is a dict
                                    of RescuePointId → True.
        new_assignments:            Rescue task assignments to register.
        waypoints_to_clear:         Robot IDs whose current_waypoint → None.
        search_task_ids_to_mark_done: Search task IDs to mark DONE (all their
                                    rescue points are now found).
    """

    rescue_found_updates: dict[TaskId, dict[RescuePointId, bool]] = field(default_factory=dict)
    new_assignments: list[Assignment] = field(default_factory=list)
    waypoints_to_clear: list[RobotId] = field(default_factory=list)
    search_task_ids_to_mark_done: list[TaskId] = field(default_factory=list)


def compute_search_phase_effect(
    discoveries: list[tuple[RobotId, RescuePoint, TaskId]],
    all_assignments: list[Assignment],
    search_task_states: dict[TaskId, SearchTaskState],
    task_by_id: dict[TaskId, BaseTask],
    all_rescue_points: dict[RescuePointId, RescuePoint],
    t_now: Time,
) -> SearchEffect:
    """Compute the full effect of a batch of rescue point discoveries.

    All inputs are read-only. The returned SearchEffect describes every state
    change required; the caller (Simulation._step) applies them.

    For each discovered rescue point:
    - Marks it found in rescue_found_updates
    - Allocates min_robots_needed robots from the search pool (discovering
      robot first, then sorted pool robots up to the required count)
    - Creates an Assignment for the rescue task

    After processing all discoveries, checks each affected search task: if
    all its rescue points are now found, includes it in search_task_ids_to_mark_done.

    Args:
        discoveries:         (robot_id, rescue_point, search_task_id) per discovery.
        all_assignments:     Active assignments this tick (to find search pool).
        search_task_states:  Current SearchTaskState per search task id.
        task_by_id:          All task definitions (to read min_robots_needed).
        all_rescue_points:   Full set of rescue points in the environment.
        t_now:               Current simulation time.
    """
    effect = SearchEffect()

    # Track which robots are still available in the search pool per task.
    # Build it once; shrink as robots are allocated to rescue tasks.
    search_pool_by_task: dict[TaskId, list[RobotId]] = {}
    for a in all_assignments:
        task = task_by_id.get(a.task_id)
        if isinstance(task, SearchTask):
            search_pool_by_task[a.task_id] = sorted(a.robot_ids)

    remaining_pool_by_task: dict[TaskId, list[RobotId]] = {
        tid: list(rids) for tid, rids in search_pool_by_task.items()
    }

    for robot_id, rescue_point, search_task_id in discoveries:
        # Mark rescue point found
        effect.rescue_found_updates.setdefault(search_task_id, {})[rescue_point.id] = True

        # Determine how many robots to allocate
        rescue_task = task_by_id.get(rescue_point.rescue_task_id)
        min_needed = getattr(rescue_task, "min_robots_needed", 1)

        pool = remaining_pool_by_task.get(search_task_id, [])
        allocated: list[RobotId] = []

        # Discovering robot gets priority
        if robot_id in pool:
            allocated.append(robot_id)
            pool.remove(robot_id)

        # Fill remaining slots from pool (already sorted for determinism)
        for rid in list(pool):
            if len(allocated) >= min_needed:
                break
            allocated.append(rid)
            pool.remove(rid)

        effect.waypoints_to_clear.extend(allocated)
        effect.new_assignments.append(Assignment(
            task_id=rescue_point.rescue_task_id,
            robot_ids=frozenset(allocated),
            assign_at=t_now,
        ))

    # Check if any search task now has all rescue points found
    for search_task_id, found_updates in effect.rescue_found_updates.items():
        state = search_task_states[search_task_id]
        # Merge current state with this tick's updates
        merged = {**state.rescue_found, **found_updates}
        if all(merged.get(rp_id, False) for rp_id in all_rescue_points):
            effect.search_task_ids_to_mark_done.append(search_task_id)

    return effect
