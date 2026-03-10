# Simulation Test Plan

Goal: stabilize the simulation suite before adding new features. Every behavioral contract should be enforced by a test. This document describes what is missing, why it matters, and the order to implement it.

---

## Current State

| File | Layer | Tests |
|---|---|---|
| `test_astar.py` | unit / algorithms | 11 — solid |
| `test_work_eligibility.py` | unit / algorithms | 29 — solid |
| `test_movement_planner.py` | unit / algorithms | exists, coverage unknown |
| `test_rescue_handler.py` | unit / algorithms | exists, coverage unknown |
| `test_search_goal.py` | unit / algorithms | exists, coverage unknown |
| `test_search_rescue.py` | integration / algorithms | 12 — partial |
| `task_state.py` state machine | — | **zero tests** |
| `robot.py` execution model | — | **zero tests** |
| `environment.py` invariants | — | **zero tests** |
| `simple_assignment.py` | — | **zero tests** |
| `snapshot.py` immutability | — | **zero tests** |
| `simulation.run()` end-to-end | — | **zero tests** |

---

## Proposed File Structure

```
tests/
  fixtures/
    scenarios/
      test_basic_completion.json     # 2 robots, 2 tasks, small grid — happy path
      test_time_budget_exceeded.json # task that cannot complete in time
      test_dependencies.json         # task B depends on task A
      test_search_rescue_e2e.json    # search + rescue full flow (may reuse existing)
  unit/
    domain/
      test_task_state.py             # NEW
      test_robot_execution.py        # NEW
      test_environment.py            # NEW
      test_snapshot.py               # NEW
    algorithms/
      test_simple_assignment.py      # NEW
      test_astar.py                  # exists
      test_work_eligibility.py       # exists
      test_movement_planner.py       # exists
      test_rescue_handler.py         # exists
      test_search_goal.py            # exists
  integration/
    engine/
      test_simulation_e2e.py         # NEW — highest priority
      test_simulation_step.py        # NEW
    algorithms/
      test_search_rescue.py          # exists
```

---

## Implementation Order

Priority is ordered by risk: things that are most likely to silently break when features are added come first.

---

### Phase 1 — Domain State Machine (highest risk, zero coverage)

**`tests/unit/domain/test_task_state.py`**

The task lifecycle is the central behavioral contract. Every transition must be tested independently.

Post-refactor model:
- `TaskStatus` has only two values: `DONE` and `FAILED` (both terminal).
- `status: None` is the non-terminal state — covers both "not started" and "in progress".
- Whether a task is "not started" vs "in progress" is determined by `started_at` (`None` = not started).
- Assignment data (`robot_ids`) no longer lives in `TaskState` — it lives in `Assignment` objects.

Contracts to enforce:

| Test | What it asserts |
|---|---|
| `test_initial_state_is_not_terminal` | fresh `TaskState` has `status=None`, `started_at=None`, `work_done=Time(0)` |
| `test_apply_work_sets_started_at` | first `apply_work()` sets `started_at = t_now`; `status` remains `None` |
| `test_apply_work_accumulates_correctly` | `work_done` increases by `dt` per tick |
| `test_apply_work_completes_task` | `work_done >= required_work_time` → `status=DONE`, `completed_at` set |
| `test_apply_work_on_done_is_noop` | already `DONE` → no state change |
| `test_apply_work_on_failed_is_noop` | already `FAILED` → no state change |
| `test_mark_done_sets_status_and_time` | `mark_done()` → `status=DONE`, `completed_at == t_now` |
| `test_mark_done_without_prior_work` | `mark_done()` on a task with `work_done=0` still sets `DONE` (rescue handler use case) |
| `test_mark_failed_sets_status_and_time` | `mark_failed()` → `status=FAILED`, `completed_at == t_now` |
| `test_started_at_not_overwritten` | second `apply_work()` does not overwrite `started_at` |

---

**`tests/unit/domain/test_robot_execution.py`**

Battery drain rates are hardcoded constants — validate them explicitly so a future refactor doesn't silently change the physics.

Note: `RobotState` has no battery floor — battery goes below zero when depleted. The test confirms this behavior rather than asserting a floor.

Contracts to enforce:

| Test | What it asserts |
|---|---|
| `test_step_to_drains_move_battery` | `battery_level` decreases by `0.001` after `step_to()` |
| `test_work_drains_work_battery` | `battery_level` decreases by `0.002` after `work()` |
| `test_idle_drains_idle_battery` | `battery_level` decreases by `0.0005` after `idle()` |
| `test_battery_goes_below_zero_when_depleted` | drain on robot with `battery_level=0.0` → `battery_level < 0.0` (no floor enforced) |
| `test_multi_tick_accumulation` | 3 calls to `step_to()` → correct cumulative drain |

---

### Phase 2 — Environment Invariants

**`tests/unit/domain/test_environment.py`**

The environment is the spatial source of truth. Its invariants protect pathfinding and eligibility from invalid state.

Contracts to enforce:

| Test | What it asserts |
|---|---|
| `test_place_accepts_valid_position` | object placed → `get_at()` returns it |
| `test_place_rejects_out_of_bounds` | raises on negative or >= width/height |
| `test_place_rejects_occupied_cell` | placing on non-empty cell raises |
| `test_in_bounds_corners` | all four corners are valid |
| `test_in_bounds_edges` | positions at width-1 and height-1 are valid; width and height are not |
| `test_add_obstacle_blocks_cell` | obstacle placed → `is_empty()` returns False |
| `test_add_zone_registers_cells` | zone added → `get_zone(id)` returns it, cells are in zone |
| `test_add_rescue_point_registered` | rescue point added → appears in `.rescue_points` |
| `test_is_empty_on_fresh_grid` | new environment → all cells empty |

---

### Phase 3 — Assignment Algorithm

**`tests/unit/algorithms/test_simple_assignment.py`**

The assignment algorithm has special-case branches (SEARCH = all robots, RESCUE = skip) that must be pinned.

Contracts to enforce:

| Test                                       | What it asserts                                                                        |
|--------------------------------------------|----------------------------------------------------------------------------------------|
| `test_assigns_capable_robot_to_task`       | task with capability requirement → only capable robot assigned                         |
| `test_does_not_double_assign_robot`        | robot assigned to task 1 → not also assigned to task 2                                 |
| `test_search_task_gets_all_capable_robots` | `SEARCH` task → all capable robots in same assignment                                  |
| `test_rescue_task_is_skipped`              | `RESCUE` task → not present in returned assignments                                    |
| `test_no_capable_robot_returns_empty`      | task requires cap no robot has → no assignment returned                                |
| `test_robots_assigned_to_at_most_one_task` | no robot should be repeated in the returned list of assignments                        |
| `test_tasks_allowed_to_have_no_assignment` | not all tasks have to have an assignment, for example if no robots meet the capability |

---

### Phase 4 — Snapshot Immutability

**`tests/unit/domain/test_snapshot.py`**

Snapshot correctness is a silent failure mode — mutations to live state could silently corrupt history.

Contracts to enforce:

| Test | What it asserts |
|---|---|
| `test_snapshot_robot_state_is_not_live` | mutate live `robot_state.position` → snapshot unchanged |
| `test_snapshot_task_state_is_not_live` | mutate live `task_state.status` → snapshot unchanged |
| `test_snapshot_dicts_are_read_only` | assigning to `snapshot.robot_states[id]` raises `TypeError` |
| `test_snapshot_reflects_state_at_time_of_call` | take snapshot, then mutate → snapshot still has old values |

---

### Phase 5 — E2E Simulation Run (the critical gap)

**`tests/fixtures/scenarios/test_basic_completion.json`**

A minimal scenario:
- Grid: 10×10
- Robots: 2, each with `MANIPULATION` capability, starting at different positions
- Tasks: 2 `ROUTINE_INSPECTION` tasks, `required_work_time: 3`, no dependencies, no deadline, spatial constraint pointing each robot toward a distinct location
- Expected: both tasks complete well within a 100-tick budget

**`tests/integration/engine/test_simulation_e2e.py`**

Contracts to enforce:

| Test | What it asserts |
|---|---|
| `test_loads_scenario_from_json` | `load_simulation("test_basic_completion.json")` does not raise; returns `Simulation` |
| `test_run_completes_all_tasks` | `result.completed == True`, `result.tasks_succeeded == result.tasks_total` |
| `test_run_returns_correct_makespan` | `result.makespan` is a `Time` with `tick > 0` |
| `test_snapshots_recorded_each_tick` | `len(sim.history) == result.makespan.tick` |
| `test_all_tasks_done_at_end` | every `task_state.status == DONE` for non-IDLE tasks |
| `test_time_budget_exceeded_returns_not_completed` | scenario with impossibly short budget → `result.completed == False` |
| `test_idle_tasks_do_not_block_completion` | IDLE task present → `run()` still terminates when others complete |
| `test_on_tick_callback_called_each_tick` | `on_tick` callback invoked exactly `makespan.tick` times |

**Additional scenario files as needed:**
- `test_dependencies.json` → task B only starts after task A is DONE; assert B's `started_at > A's completed_at`
- `test_time_budget_exceeded.json` → task with `required_work_time` far beyond `max_delta_time`

---

### Phase 6 — Engine Step Contracts

**`tests/integration/engine/test_simulation_step.py`**

These tests call `_step()` directly (or drive `run()` for a fixed number of ticks) to pin the per-tick behavioral contracts.

Contracts to enforce:

| Test | What it asserts |
|---|---|
| `test_step_increments_time` | `t_now` advances by `dt` each step |
| `test_step_records_snapshot_in_history` | `history[t_now]` exists after each step |
| `test_work_accumulates_with_two_robots` | 2 robots on same task → `work_done` increases by 2×dt per tick |
| `test_work_does_not_accumulate_with_zero_eligible` | robot outside spatial constraint → `work_done` unchanged |
| `test_dependency_blocks_work` | task B not started while task A is not DONE |
| `test_deadline_blocks_work` | task past deadline → `work_done` never increases |
| `test_battery_depletion_stops_work` | robot drained to 0 → task stops progressing |
| `test_no_two_robots_share_cell` | after each step, all robot positions are unique |
| `test_robot_to_task_mapping_correct` | after assignment applied, `robot_to_task` maps correctly |

---

## Summary Table

| Phase | File | Priority |
|---|---|---|
| 1 | `test_task_state.py` | Critical — core state machine |
| 1 | `test_robot_execution.py` | Critical — battery physics |
| 2 | `test_environment.py` | High — spatial invariants |
| 3 | `test_simple_assignment.py` | High — assignment contracts |
| 4 | `test_snapshot.py` | Medium — immutability guarantee |
| 5 | `test_simulation_e2e.py` + JSON fixture | Critical — full run contract |
| 6 | `test_simulation_step.py` | High — per-step sub-contracts |
