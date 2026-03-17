# Refactor Plan

## Motivation

The current `Simulation` class conflates state storage, business rule enforcement, movement resolution,
termination logic, and event handling. Rules are scattered across `filter_assignments_for_eligible_robots`,
`plan_moves`, `_snapshot_work_eligibility`, `_find_rescue_discoveries`, and `_apply_search_effect`.
This refactor establishes a single responsibility for each component and a single place for all business rules.

---

## Component Contracts (one sentence each)

| Component | Contract |
|---|---|
| `Assignment` | A plain frozen `(task_id, robot_id)` tuple — no timestamp, no grouping, no logic. |
| `BaseAssignmentService` | Read and write the current set of one-per-robot assignments; upsert semantics, last write wins. |
| `BaseTaskRegistry` | Read and write the live task queue — the set of currently actionable task definitions visible to an assigner. |
| `classify_step` (Observer) | Pure function — given state and assignments, returns a `StepOutcome` describing exactly what happens this tick; **the single place all business rules live.** |
| `apply_outcome` (Applicator) | Pure function — given state and a `StepOutcome`, returns new state; applies deltas mechanically with no validity checks or business logic. |
| `SimulationState` | Immutable, self-contained snapshot of all runtime data for one tick — sufficient to render a view or replay the simulation without any external references. |
| `StepOutcome` | Immutable record of everything that happened in one tick — the delta between two states; consumed by the runner, views, and reactive assigners. |
| `SimulationRunner` | Orchestrates one tick: syncs registry into state, reads assignments, calls `step()`, writes spawned tasks back to registry; no business logic, returns `(SimulationState, StepOutcome)`. |
| `step()` | Thin pure wrapper that chains `classify_step → apply_outcome` and returns both results; exists so the pipeline is testable without the runner's services. |

---

## Key Design Rules

- **Business rules live in `classify_step` only.** If you find a validity check anywhere else, it belongs in the observer.
- **`apply_outcome` never rejects.** Invalid assignments produce an `assignments_ignored` entry in `StepOutcome` and are logged as data, not errors.
- **State objects are frozen.** `SimulationState`, `RobotState`, `TaskState`, `SearchTaskState`, and `BaseTaskState` are all `frozen=True` — new instances are constructed each tick, never mutated.
- **`TaskState` is lazy.** A task has no entry in `task_states` until a robot first works on it; the applicator creates the initial entry on the first work tick.
- **`rescue_found` is a frozenset of found IDs.** Absence means unfound; the full expected set comes from `state.environment.rescue_points`, not from the task state.
- **Rescue tasks are not pre-seeded.** When a robot discovers a rescue point, `StepOutcome.tasks_spawned` contains the `RescuePoint`; the runner writes it to the registry; assigners react next tick.
- **Task streaming replaces dependency edges.** A task that cannot start yet simply does not exist in the registry — no dependency fields needed.
- **The runner is the only orchestration seam.** Callers interact with the simulation exclusively through `runner.step()` — no direct access to observer, applicator, or services.

---

## What Gets Removed

| Current | Fate |
|---|---|
| `filter_assignments_for_eligible_robots` | Absorbed into `classify_step` |
| `_find_rescue_discoveries` | Absorbed into `classify_step` |
| `_apply_search_effect` | Absorbed into `classify_step` / `apply_outcome` |
| `compute_search_phase_effect` | Absorbed into `classify_step` |
| `_snapshot_work_eligibility` | Absorbed into `classify_step` |
| `EventEmitter` | Removed — listeners read `StepOutcome` directly |
| `TaskType.RESCUE` | Removed — rescue is a plain spatial work task spawned dynamically |
| Task `dependencies` field | Removed — ordering expressed through task registry queue |
| Task `deadline` field | Removed — intentionally dropped in new design |
| Old time-based `Assignment` (with `assign_at`) | Removed — new assignment is stateless, last-write-wins |
| `Simulation.run()` as primary interface | Replaced by `SimulationRunner.step()` |
| `rescue_found: dict[TaskId, bool]` | Replaced by `rescue_found: frozenset[TaskId]` |
| `apply_work`, `move_robot`, `work_robot`, `idle_robot` mutation functions | Will be removed when old engine is deleted (Phase 6); currently kept alive via `object.__setattr__` |

---

## Step Flow

```
assignments = AssignmentService.get_current()
tasks       = TaskRegistry.all()              # synced into state each tick by runner
outcome     = classify_step(state, assignments, pathfinding)   # all rules here
new_state   = apply_outcome(state, outcome)                    # pure mutation
              TaskRegistry.add(task) for task in outcome.tasks_spawned
state       = new_state
return new_state, outcome                     # caller renders view or reacts
```

---

## StepOutcome Shape

```python
@dataclass
class StepOutcome:
    moved:               list[tuple[RobotId, Position]]        # destination only — battery drain derived in apply_outcome
    worked:              list[tuple[RobotId, TaskId]]          # battery drain derived in apply_outcome
    tasks_completed:     list[TaskId]
    tasks_spawned:       list[BaseTask]                        # written to TaskRegistry by runner
    assignments_ignored: list[tuple[Assignment, IgnoreReason]] # logged as data, not errors
    rescue_points_found: list[TaskId]                         # lets apply_outcome update SearchTaskState.rescue_found
    waypoints:           dict[RobotId, Position]              # proposed waypoint per robot; applied to RobotState by apply_outcome

# idle robots = any robot not in moved or worked — derived, not stored
# battery drain = derived in apply_outcome from moved/worked/idle classification

class IgnoreReason(Enum):
    NO_BATTERY        # robot battery depleted
    WRONG_CAPABILITY  # robot lacks required capabilities
    TASK_TERMINAL     # task already done or failed
    NO_PATH           # pathfinding cannot reach task location
```

---

## Incremental Migration Strategy

**Rule: new code goes in new files. Old code is never touched until its replacement is verified.**

---

### Phase 1 — Build the new core ✅ COMPLETE

- `simulation/engine_rewrite/step_outcome.py` — `StepOutcome`, `IgnoreReason`
- `simulation/engine_rewrite/observer.py` — `classify_step()` pure function
- `simulation/engine_rewrite/applicator.py` — `apply_outcome()` pure function
- `simulation/engine_rewrite/step.py` — `step()` thin wrapper
- `simulation/engine_rewrite/simulation_state.py` — `SimulationState` frozen dataclass
- `simulation/engine_rewrite/assignment.py` — new flat `Assignment` frozen dataclass
- Full unit test coverage for observer, applicator, step

---

### Phase 2 — Build new services and runner ✅ COMPLETE

- `simulation/engine_rewrite/services/base_task_registry.py` — `BaseTaskRegistry` ABC
- `simulation/engine_rewrite/services/in_memory_task_registry.py` — in-memory implementation
- `simulation/engine_rewrite/services/base_assignment_service.py` — `BaseAssignmentService` ABC
- `simulation/engine_rewrite/services/in_memory_assignment_service.py` — in-memory implementation with upsert semantics
- `simulation/engine_rewrite/runner.py` — `SimulationRunner` orchestrator, returns `(SimulationState, StepOutcome)`
- Frozen all runtime state objects (`RobotState`, `TaskState`, `SearchTaskState`, `BaseTaskState`)
- `rescue_found` migrated from `dict[TaskId, bool]` to `frozenset[TaskId]`
- Lazy `TaskState` initialisation — created on first work tick, not pre-seeded
- Full unit test coverage for services, runner, search/rescue discovery and completion

---

### Phase 3 — Build new runner and verify end-to-end 🔲 TODO

- `main_v2.py` — new entry point using `SimulationRunner`, `InMemoryTaskRegistry`, `InMemoryAssignmentService`
- Run both `main.py` and `main_v2.py` against the same scenarios and compare outcomes tick-by-tick
- `tests/integration/engine_rewrite/` — end-to-end integration tests (search-and-rescue, multi-robot, battery drain)
- New scenario loader that builds `SimulationState` and populates the new services (no rescue task pre-seeding)

---

### Phase 4 — Migrate the simulation view 🔲 TODO

- Update `SimulationView` to render from `SimulationState` + `StepOutcome` instead of `SimulationSnapshot`
- View reads task definitions from `state.tasks`, robot positions from `state.robot_states`, progress from `state.task_states`
- Keep old rendering path alive until new one is verified against existing scenarios

---

### Phase 5 — Migrate the MCP server 🔲 TODO

- Update `StateService` to write the new `SimulationState` schema to `sim_state.json`
- Update MCP tools to read new schema
- `assign_robots` tool: keep grouped `robot_ids` interface for LLM ergonomics, flatten to `Assignment` list internally before writing to `AssignmentService`
- `stop_all_robots`: clearing assignments replaces the old IDLE_TASK_ID pattern
- Update MCP README and tool docstrings

---

### Phase 6 — Delete old code 🔲 TODO

Only after all dependents are on the new path and all tests pass:

- Delete `simulation/engine/` entirely
- Delete `filter_assignments_for_eligible_robots`, `compute_search_phase_effect`, `_find_rescue_discoveries`, `_apply_search_effect`, `_snapshot_work_eligibility`
- Delete old `Assignment` dataclass (with `robot_ids` frozenset and `assign_at`)
- Remove `apply_work`, `move_robot`, `work_robot`, `idle_robot` mutation functions and their `object.__setattr__` shims
- Delete `TaskType.RESCUE`, `task.deadline`, `task.dependencies` fields from domain models
- Rename `simulation/engine_rewrite/` → `simulation/engine/`
- Delete `main.py`, rename `main_v2.py` → `main.py`
- Delete skipped integration tests in `tests/integration/algorithms/test_search_rescue.py`
