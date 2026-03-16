# Refactor Plan

## Motivation

The current `Simulation` class conflates state storage, business rule enforcement, movement resolution,
termination logic, and event handling. Rules are scattered across `filter_assignments_for_eligible_robots`,
`plan_moves`, `_snapshot_work_eligibility`, `_find_rescue_discoveries`, and `_apply_search_effect`.
This refactor establishes a single responsibility for each component and a single place for all business rules.

---

## Component Responsibilities (one sentence each)

### `Assignment` (data)
A plain tuple of `(task_id, robot_id)` — no timestamp, no grouping, no logic.

### `AssignmentService`
Only reads and writes the current set of assignments to/from a backing store.

### `StateService`
Only reads and writes the full simulation state (robot positions, battery, task progress) to/from a backing store.

### `TaskRegistry`
Only reads and writes the live task queue — the window of currently actionable tasks visible to the assigner.

### `Observer` (`classify_step`)
A pure function that takes current state and current assignments and produces a `StepOutcome` — **this is the single place all business rules live.**

### `Simulation` (`apply_outcome`)
A pure function that takes current state and a `StepOutcome` and returns new state — resolves movement and applies state mutations with no validity checks.

### `SimulationRunner`
Only drives the step loop — calls `Observer → Simulation` in sequence, wires services together, and notifies listeners with the raw `StepOutcome`; contains no business logic.

### `Assigner`
A pluggable callback (LLM or algorithm) that reads the full `TaskRegistry` and current robot states, then writes new assignments to `AssignmentService` — called by the orchestrator when `StepOutcome` warrants re-assignment.

### `MetricService`
Only receives `StepOutcome` each tick and records outcomes (wasted ticks, blocked robots, invalid assignments, etc.) as data — never influences simulation execution.

---

## Key Design Rules

- **Business rules live in `Observer` only.** If you find a validity check anywhere else, it belongs in `Observer`.
- **`Simulation` never rejects.** Invalid assignments are not filtered — they produce an `assignments_ignored` entry in `StepOutcome` and get logged as data.
- **`step()` is pure.** `Observer` and `Simulation` are both pure functions — same inputs always produce same outputs, no service calls, no side effects.
- **No `EventEmitter`.** Listeners receive `StepOutcome` directly — `IgnoreReason` already carries the semantic meaning of every negative outcome. Named events add no value.
- **The runner never calls the assigner directly.** The orchestrator wires the assigner as a conditional listener: `if outcome.tasks_completed: assigner(outcome)`.
- **Task streaming replaces dependencies.** A task that cannot start yet simply does not exist in the registry yet — no dependency edges needed.
- **Rescue tasks are not seeded.** When a search task completes, `StepOutcome.tasks_spawned` contains the generated rescue task; the runner writes it to the registry; the assigner reacts.

---

## What Gets Removed

| Current | Fate |
|---|---|
| `filter_assignments_for_eligible_robots` | Absorbed into `Observer` as outcome classification |
| `_find_rescue_discoveries` | Absorbed into `Observer` |
| `_apply_search_effect` | Absorbed into `Observer` / `apply_outcome` |
| `compute_search_phase_effect` | Absorbed into `Observer` |
| `_snapshot_work_eligibility` | Absorbed into `Observer` |
| `EventEmitter` | Removed — listeners read `StepOutcome` directly |
| `TaskType.RESCUE` | Removed — rescue is a plain spatial work task spawned dynamically |
| Task `dependencies` field | Removed — ordering expressed through task registry queue |
| `Simulation.run()` as primary interface | Demoted to thin convenience wrapper over `step()` |
| Scattered `isinstance` task-type checks across engine | Replaced by typed `StepOutcome` fields |

---

## Step Flow

```
assignments = AssignmentService.read()
outcome     = Observer.classify_step(state, assignments)   # all rules here
new_state   = Simulation.apply_outcome(state, outcome)     # pure mutation
              StateService.write(new_state)
              TaskRegistry.append(outcome.tasks_spawned)
              for listener in listeners:
                  listener(outcome)                        # MetricService, Assigner, etc.
state       = new_state
```

---

## StepOutcome Shape

```python
@dataclass
class StepOutcome:
    moved:               list[tuple[RobotId, Position]]         # destination only — battery drain derived in apply_outcome
    worked:              list[tuple[RobotId, TaskId]]           # battery drain derived in apply_outcome
    tasks_completed:     list[TaskId]
    tasks_spawned:       list[BaseTask]                         # written to TaskRegistry by runner
    assignments_ignored: list[tuple[Assignment, IgnoreReason]]  # logged as data, not errors
    rescue_points_found: list[tuple[TaskId, RescuePointId]]     # intentional: lets apply_outcome update
                                                                # SearchTaskState.rescue_found without
                                                                # re-running discovery logic (business rules
                                                                # must not leak into apply_outcome)
    waypoints:           dict[RobotId, Position]                # proposed waypoint per robot this tick;
                                                                # written by Observer, applied to
                                                                # RobotState.current_waypoint by apply_outcome

# idle robots = any robot not in moved or worked — derived, not stored
# battery drain = derived in apply_outcome from moved/worked/idle classification

class IgnoreReason(Enum):
    NO_BATTERY        # robot_died event equivalent
    WRONG_CAPABILITY  # invalid assignment
    TASK_TERMINAL     # wasted assignment
    NO_PATH           # robot blocked

# Note: OUT_OF_RANGE was removed. A robot moving toward a task it cannot yet
# work on is a valid in-progress assignment — the assignment is not ignored,
# the robot simply moves. OUT_OF_RANGE would conflate "robot is on the way"
# with "assignment is invalid", which blurs Observer's classification.
```

---

## Incremental Migration Strategy

The MCP server, JSON services, and simulation view all depend on the current contracts.
The goal is to never break the existing `main.py` path until a proven replacement exists.
Each phase ends with all existing tests passing and new tests added for the new code.

**Rule: new code goes in new files. Old code is never touched until its replacement is verified.**

---

### Phase 1 — Build the new core in total isolation

New files only, all under `simulation/engine_rewrite/`. Zero changes to existing code. Zero risk.

- `simulation/engine_rewrite/__init__.py`
- `simulation/engine_rewrite/step_outcome.py` — `StepOutcome`, `IgnoreReason`
- `simulation/engine_rewrite/observer.py` — `classify_step()` pure function (all business rules)
- `simulation/engine_rewrite/applicator.py` — `apply_outcome()` pure function (state mutation only)
- `simulation/engine_rewrite/step.py` — `step(state, assignments) -> (SimulationState, StepOutcome)`
- `tests/unit/engine_rewrite/` — unit tests for all of the above, no services, no files, no MCP

At the end of this phase: new core is fully tested. Old `main.py` still runs unchanged.

---

### Phase 2 — Build new services alongside old ones

New files under `simulation/engine_rewrite/`. Old services untouched.

- `simulation/engine_rewrite/task_registry.py` — `TaskRegistry` (JSON-backed, flat task queue)
- `simulation/engine_rewrite/assignment.py` — flat `Assignment = tuple[TaskId, RobotId]` alongside old `Assignment` dataclass
- `tests/unit/engine_rewrite/` — tests for new services in isolation

At the end of this phase: new services tested. Old MCP still reads/writes old files unchanged.

---

### Phase 3 — Build new runner and verify end-to-end

- `main_v2.py` — new orchestrator using `step()`, `TaskRegistry`, new services
- Run both `main.py` and `main_v2.py` against the same scenarios and compare outcomes
- `tests/integration/engine_rewrite/` — integration tests covering search-and-rescue end-to-end
- New scenario loader variant that does not seed rescue tasks

At the end of this phase: two working runners side by side. Old path untouched.

---

### Phase 4 — Migrate the simulation view

- Update `SimulationView` to render from new `SimulationState` + `StepOutcome` instead of `SimulationSnapshot`
- Keep old `SimulationView` rendering path alive until new one is verified
- The view should never access task/robot state types directly — only flat data from state and outcome

---

### Phase 5 — Migrate the MCP server

The MCP is the highest-risk migration because it is an external contract the LLM depends on.

- Update `StateService` to write the new state schema to `sim_state.json`
- Update MCP tools to read new schema — `work_done_ticks` goes away, task type info becomes richer
- `assign_robots` tool: keep grouped `robot_ids` in the MCP interface (ergonomic for LLMs) but flatten internally before writing to `AssignmentService`
- `stop_all_robots` / `IDLE_TASK_ID`: revisit — with streaming, stopping robots means clearing assignments, not assigning to a no-op task
- Update MCP README and tool docstrings to reflect new concepts

---

### Phase 6 — Delete old code

Only after all dependents are on the new path and all tests pass:

- Delete old `Simulation` class and `simulation/engine/` contents
- Delete `filter_assignments_for_eligible_robots`, `compute_search_phase_effect`, `_find_rescue_discoveries`, `_apply_search_effect`, `_snapshot_work_eligibility`
- Delete old `Assignment` dataclass (with `robot_ids` frozenset and `assign_at`)
- Delete `TaskType.RESCUE`, task `dependencies` field
- Rename `simulation/engine_rewrite/` → `simulation/engine/`
- Delete `main.py`, rename `main_v2.py` → `main.py`
- Remove any dead scenario loader paths
