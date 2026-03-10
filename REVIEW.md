# Simulation Codebase Review

Goal: identify what's clean, what's noisy, and what should change to promote readability and simplicity.

---

## What's Done Well

**Immutable/mutable separation is consistent and correct.**
Every domain object has a paired pattern: `Robot` / `RobotState`, `Task` / `TaskState`. Immutable definitions are frozen dataclasses. Mutable state is a separate plain dataclass. This is the right call and holds up throughout.

**`_step()` reads as a clear phase narrative.**
The simulation tick is a clean sequence of named private methods. A reader can skim `_step()` and understand the full tick lifecycle without reading implementation details. The recent refactor to extract phases was the right move.

**Pure functions are extracted correctly.**
`movement_planner`, `work_eligibility`, `rescue_handler`, `search_goal` are all stateless modules that take explicit inputs and return values. No hidden state, no `self`. This makes them easy to test and reason about in isolation.

**`StepContext` bundle is a good idea.**
Grouping the per-tick read-only slices into one object prevents threading 6+ individual params through every function. The concept is sound.

**`Assignment` as temporal immutable data is clean.**
Timestamped, frozen, pure data. The "most recent assignment <= t_now wins" resolution model is simple and replay-friendly.

**`SimulationSnapshot` immutability is well-designed.**
`MappingProxyType`, frozen dataclass, copied state objects — the snapshot boundary is genuinely protected. The `snapshot()` copy logic is explicit and correct.

**Collision resolution algorithm is clean.**
`resolve_collisions` is a tight, well-documented iterative algorithm with a clear convergence argument. Easy to read, easy to test.

**`Position` and `Zone` are minimal and correct.**
Small, frozen, no bloat. `manhattan()` where needed, `contains()` on Zone — nothing extra.

---

## Issues by Module

### `simulation.py`

**`_plan_robot_moves` takes `robot_to_task` twice.**
The method signature is `_plan_robot_moves(self, ctx, robot_to_task)`. But `robot_to_task` is already on `ctx.robot_to_task`. The closure inside uses the outer `robot_to_task` instead of `ctx.robot_to_task`. The parameter is redundant — remove it and read from `ctx`.

```python
# simulation.py:207-222 — robot_to_task is passed separately AND lives on ctx
def _plan_robot_moves(self, ctx: StepContext, robot_to_task: dict[RobotId, TaskId]):
    def _goal_resolver(robot_id, state):
        task = self._task_by_id[robot_to_task[robot_id]]  # ← should be ctx.robot_to_task
```

**`_resolve_task_target_position` is a trivial one-liner wrapper.**
It exists only to partially apply `self.environment`. The caller (`_goal_resolver` closure) already has `self.environment` in scope — just call `resolve_task_target_position(task, state.position, self.environment)` directly and delete the method.

```python
# simulation.py:334-335 — zero abstraction value
def _resolve_task_target_position(self, task, robot_pos):
    return resolve_task_target_position(task, robot_pos, self.environment)
```

**`snapshot()` calls `get_assignments_for_time` a second time every tick.**
`_step()` already calls `_get_active_assignments()` at the top. Then `snapshot()` (called at the end of `_step()`) calls `assignment_service.get_assignments_for_time(self.t_now)` again independently. Pass `assignments` into `snapshot()` or cache it on the step.

**`__post_init__` None checks are noise.**
`if self.environment is None: raise ValueError(...)` for every field. These aren't typed as `Optional`, so the only way they're `None` is a caller ignoring types. These checks don't validate semantic correctness (e.g. robot_ids consistent between `robots` and `robot_states`) and add 10 lines of ceremony for no real protection.

**Untyped `rescue_found` field.**
```python
rescue_found: dict = field(default_factory=dict)  # dict[RescuePointId, bool]
```
The comment says what the type is. Just type it: `dict[RescuePointId, bool]`.

**`_find_rescue_discoveries` returns `list[object]`.**
It clearly returns `list[RescuePoint]`. The annotation is wrong and forces `_trigger_rescue_found` to also accept `object`. Type it correctly.

**`Optional` import is unused style.**
`from typing import Optional` — the codebase already uses `X | None` consistently. `Optional[Callable[...]]` on line 115 should match.

---

### `task.py`

**Methods on `Task` that mutate `TaskState` are the biggest design smell.**
`Task` is documented as "immutable, declarative, contains NO execution state." But `set_assignment`, `apply_work`, `mark_done`, `mark_failed` are instance methods on `Task` that mutate an external `TaskState` object passed in. These methods do not use `self` in any meaningful way — they're just functions that happen to live on `Task` to pick up `required_work_time`.

This creates a confusing split: state lives on `TaskState`, but the logic for transitioning that state lives on `Task`. A reader of `TaskState` has to know to look at `Task` for behavior, and vice versa.

Options:
- Move these to `task_state.py` as standalone functions, passing `required_work_time` explicitly where needed
- Or keep them on `Task` and stop calling it "immutable declarative data" in the docstring — it's actually a domain object with behavior

**Local imports repeated 4 times to avoid a cycle.**
`from .task_state import TaskStatus` appears inside `set_assignment`, `apply_work`, `mark_done`, `mark_failed`. This is the cycle: `task.py → task_state.py` and `task_state.py → task.py` (for `TaskId`). Fix: move `TaskId` to a shared `types.py` or to `task.py` only, then `task_state.py` can import from `task.py` normally, or vice versa.

**`TaskType` mixes domain types with mechanics types.**
`ROUTINE_INSPECTION`, `ANOMALY_INVESTIGATION`, `PREVENTIVE_MAINTENANCE`, `EMERGENCY_RESPONSE`, `PICKUP` — the simulation never specially handles these; they're all just "do work at a location."
`IDLE`, `SEARCH`, `RESCUE` — the simulation has specific branching logic for each.

The simulation's special-casing branches (in `plan_moves`, `_snapshot_work_eligibility`, `_advance_task_progress`) only care about `IDLE`, `SEARCH`, `RESCUE`. The five "domain" types are interchangeable from the sim's perspective. This may be intentional for research, but the mixed abstraction levels mean adding a new mechanic task type requires tracing through all the special-case branches.

---

### `step_context.py`

**The name "snapshot" is misleading.**
The docstring says "Snapshot of simulation state for a single tick." But `robot_states` and `task_states` are the live mutable dicts — not copies. Mutations during movement planning will be visible here. It's a parameter bundle, not a snapshot. Call it what it is.

**`robot_to_task` on `StepContext` vs `robot_to_task` passed separately.**
`StepContext` carries `robot_to_task`, but `_plan_robot_moves` also receives it as a second argument. One of these should go away (the argument, not the context field).

---

### `movement_planner.py`

**`PathfindingAlgorithm` type alias is defined in three places.**
`simulation.py:39`, `movement_planner.py:21`, `search_goal.py:18`. Define it once (in `movement_planner.py` is the natural home) and import everywhere else.

**Circular import worked around with a local import.**
```python
from simulation_models.step_context import StepContext  # local to avoid circular import
```
`plan_moves` takes a `StepContext` but can't import it at module level. The fix: `StepContext` should not import from `movement_planner`. Checking `step_context.py` — it doesn't. The issue is `movement_planner.py` imports from `task.py` and `step_context.py` imports from `task.py`, not a real cycle. This is worth investigating to remove the local import.

**`plan_moves` IDLE check duplicates knowledge spread across three sites.**
IDLE is special-cased in `plan_moves` (no movement), `_snapshot_work_eligibility` (skip), and the `eligible_by_task` loop implicitly. This is fine for now but means adding a new "no-op" task type requires touching multiple places.

---

### `work_eligibility.py`

**`pass  # in zone, eligible` is an anti-pattern.**
```python
if zone.contains(state.position):
    pass  # in zone, eligible
elif sc.max_distance == 0:
    continue
else:
    ...
```
Invert the condition. Early-exit on ineligible cases, remove the `pass`:
```python
if not zone.contains(state.position):
    if sc.max_distance == 0:
        continue
    nearest_dist = min(...)
    if nearest_dist > sc.max_distance:
        continue
```

**Five parameters passed to `get_eligible_robots`.**
`task`, `task_states`, `robots`, `robot_states`, `environment`, `time` — six total. This is on the edge of too many. The function could take a `StepContext`-like bundle, or the task-level guard checks (terminal, deadline, dependencies) could be separated from the per-robot filtering.

---

### `rescue_handler.py`

**`RescueEffect` has untyped `rescue_found_updates: dict`.**
Should be `dict[RescuePointId, bool]`.

**`compute_rescue_effect` takes `tasks: list[Task]` only to find SEARCH task IDs.**
It already receives `task_by_id: dict[TaskId, Task]` and `robot_to_task: dict[RobotId, TaskId]`. The search task IDs can be derived from these without needing the full `tasks` list:
```python
search_task_ids = list({tid for tid in robot_to_task.values() if task_by_id[tid].type == TaskType.SEARCH})
```
Remove the `tasks` parameter.

**All SEARCH tasks marked done on any rescue discovery — implicit, not documented.**
`tasks_to_mark_done=search_task_ids` marks every SEARCH task done when any single rescue point is found. This might be the correct domain behavior but it's non-obvious. It deserves a comment explaining why.

---

### `search_goal.py`

**Untyped dict parameters.**
`rescue_points: dict` and `rescue_found: dict` should be `dict[RescuePointId, RescuePoint]` and `dict[RescuePointId, bool]`.

**Magic number 1000.**
```python
for _ in range(1000):
```
Name this: `_MAX_RANDOM_SEARCH_ATTEMPTS = 1000`.

---

### `environment.py`

**`_rescue_points: dict` is untyped to avoid a circular import.**
The comment `# RescuePoint imported inside methods to avoid circular imports at module load` explains it, but the result is `add_rescue_point(self, rp: object)` — a method typed as accepting `object`. This is a real hole. Resolve the cycle (move `RescuePointId` out of `rescue_point.py`) or use `TYPE_CHECKING` imports.

**`rescue_points` property returns a new shallow copy every call.**
```python
@property
def rescue_points(self) -> dict:
    return dict(self._rescue_points)
```
Called multiple times per tick (once in `_find_rescue_discoveries`, once in `search_goal`). Use `MappingProxyType` instead — zero-copy read-only view.

**`_cell()` is a private method that just returns `(pos.x, pos.y)`.**
It's called twice (in `get_at` and `place`) and adds no abstraction. Inline it.

---

### `snapshot.py`

**Dead, broken demo code at the bottom.**
The `if __name__ == "__main__":` block references `assignment_algorithm` (line 108) and `sim.step()` (line 117), neither of which exists in the current API. Delete it or fix it.

**`t_now: "Time | None" = None` on `SimulationSnapshot`.**
Every snapshot created by `Simulation.snapshot()` passes `t_now`. Making it `Optional` is just noise — every consumer has to handle `None` that can never actually be `None`. Make it required.

---

### `assignment.py`

**`RobotId` is defined in the wrong module.**
`RobotId` is a robot identifier but lives in `assignment.py`. This forces `robot_state.py`, `robot.py`, and `work_eligibility.py` to import from `assignment.py` — a module about scheduling — just to get an ID type. Move `RobotId` to `robot.py` or a shared `types.py`.

---

## Cross-Cutting Issues

**Untyped `dict` annotations throughout.**
Pattern appears in: `Simulation.rescue_found`, `RescueEffect.rescue_found_updates`, `Environment._rescue_points`, `Environment.rescue_points` property return, `search_goal.py` parameters, `_find_rescue_discoveries` return type, `_trigger_rescue_found` parameter. All should carry full generic types.

**`robot_to_task` asymmetry with `TaskState.assigned_robot_ids`.**
`TaskState` stores `assigned_robot_ids` as persistent state. `robot_to_task` is derived fresh every tick from assignments. These represent the same relationship from opposite directions. Either:
- Accept the asymmetry (current state, fine if intentional)
- Add `current_task_id: TaskId | None` to `RobotState` and maintain it alongside `assigned_robot_ids`, eliminating `_map_robots_to_tasks` and reducing threading

**`StepContext` is named like a snapshot but is a live-reference bundle.**
Rename to `TickContext` or `StepBundle` to remove the misleading "snapshot" implication.

---

## Priority Order for Refactoring

1. **Fix the `_plan_robot_moves` double-passing of `robot_to_task`** — confusing, easy fix
2. **Delete `_resolve_task_target_position` wrapper** — pure noise
3. **Fix `snapshot()` calling `get_assignments_for_time` twice per tick** — behavior correctness concern if the service is stateful
4. **Move `RobotId` out of `assignment.py`** — bad dependency direction, affects many files
5. **Type all `dict` annotations** — low effort, high readability gain
6. **Define `PathfindingAlgorithm` once and import it** — three definitions is wrong
7. **Fix `snapshot.py` dead code and make `t_now` required**
8. **Invert the `pass` in `work_eligibility.py`**
9. **Remove the `tasks` parameter from `compute_rescue_effect`**
10. **Decide and document the `Task` methods question** — are they behavior on a domain object, or should they move to `task_state.py`?

---

## Implementation Report

All 10 priority items were addressed across 12 commits. Overall rating: **8.5 / 10**.

---

### Item 1 — `_plan_robot_moves` redundant `robot_to_task` param ✅
**Done well.** Simple drop of the parameter, closure updated to use `ctx.robot_to_task`. Clean and minimal.

---

### Item 2 — Delete `_resolve_task_target_position` wrapper ✅
**Done well.** Inlined the free function call directly in the closure. Deleted the wrapper. One less indirection for readers to trace.

---

### Item 3 — Double `get_assignments_for_time` call per tick ✅
**Done well, with a good interface decision.** `snapshot()` now accepts `active_assignments: list[Assignment] | None = None` — callers that have already fetched assignments pass them in, callers that haven't (e.g. ad-hoc `snapshot()` calls) still work via the default fetch. The `__post_init__` initial snapshot correctly passes `[]`. The parameter name and docstring are clear.

**One note:** the default `None` with conditional fetch still allows the double-call pattern to silently re-emerge if someone calls `snapshot()` without passing assignments after a step. A stricter design would make assignments required, but that would break external callers using `snapshot()` directly. The current trade-off is reasonable.

---

### Item 4 — Move `RobotId` out of `assignment.py` ✅
**Done well.** Moved to `robot_state.py`, which is the right home — it's the lowest-dependency file that already defines the other robot runtime concept. The 24-file update was handled cleanly with sed for the mechanical parts. All tests passed after.

**One note:** `robot_state.py` is now doing double duty (defines both `RobotId` and `RobotState`). A purist would put `RobotId` in `robot.py` and break the cycle differently, but that creates a circular import with `robot_state.py`. The current placement is the pragmatic correct answer given the module structure.

---

### Item 5 — Type all `dict` annotations ✅
**Mostly done.** `rescue_found`, `RescueEffect.rescue_found_updates`, `search_goal` parameters, `_find_rescue_discoveries` return type, `_trigger_rescue_found` param — all typed. The `Optional` import was also removed and the annotation updated to `X | None` style.

**Partial miss:** `Environment.rescue_points` property still returns `-> dict` (untyped). The circular import issue (`environment.py` can't import `RescuePoint` at module level without a cycle) was acknowledged but only partially addressed — the property got a comment rather than a proper type. This is the one remaining weak spot.

---

### Item 6 — `PathfindingAlgorithm` defined once ✅
**Done well.** Canonical definition stays in `movement_planner.py` (the natural home). `simulation.py` and `search_goal.py` now import from there. The previously unused `Callable` imports in both files were also cleaned up as a byproduct.

---

### Item 7 — `snapshot.py` dead code + `t_now` required ✅
**Done well.** The 70-line broken `__main__` demo was deleted outright. `t_now` made required with the docstring updated to match. All 87 tests still pass, confirming nothing relied on the `None` default.

---

### Item 8 — Invert `pass` in `work_eligibility.py` ✅
**Done well.** The if/pass/elif/else structure is now a straightforward if-not with early exits. Logic is identical, readability improved. This is the kind of change that takes 2 minutes and makes the code noticeably cleaner.

---

### Item 9 — Remove `tasks` param from `compute_rescue_effect` ✅
**Done well, with a subtle improvement.** The original `tasks` list was iterated to find all SEARCH task IDs. The replacement derives them from `task_by_id`, which is the full task map — same information, one fewer parameter. A comment was added explaining *why* all SEARCH tasks are marked done simultaneously (the non-obvious domain behavior flagged in the review). The test that verified multi-task discovery was updated to include both tasks in `task_by_id` rather than passing a stale `tasks=` list.

---

### Item 10 — `Task` methods question ⚠️ Not resolved
**Left open intentionally.** This is the largest architectural question and touches `task.py`, `task_state.py`, and every call site. The circular import (`task.py ↔ task_state.py`) that manifests as four repeated local imports is still present. The options (move methods to `task_state.py`, or clarify the docstring) were not acted on.

This is the right call for now — it's a bigger decision that should be made deliberately, not as part of a cleanup pass. But it remains the most significant unresolved design issue in the codebase.

---

### Bonus items addressed
Beyond the priority list, three additional cleanups were committed:

- **`StepContext` docstring corrected** — changed from "snapshot" to "parameter bundle" with a note that the dicts are live references. The class name itself (`StepContext`) was kept since renaming would be more churn than value.
- **Duplicate `RobotId` import in `movement_planner.py` consolidated** — two separate imports from `robot_state` collapsed into one.
- **`environment.py`: `rescue_points` → `MappingProxyType`, `_cell()` inlined** — zero-copy view replaces per-call shallow copy; trivial private method deleted.
- **`search_goal.py` magic `1000` named** — `_MAX_RANDOM_GOAL_ATTEMPTS = 1000`.
- **`__post_init__` None guards removed** — 10 lines of ceremony deleted.
- **Local import workaround in `movement_planner.py` removed** — the circular import it was guarding against doesn't actually exist; `StepContext` now imported at module level normally.

---

### What's still open

| Issue | Status |
|-------|--------|
| `Task` methods on an "immutable" object + repeated local imports | Open — architectural decision needed |
| `Environment.rescue_points` return type still `-> dict` | Partial — circular import needs structural fix |
| `robot_to_task` vs `RobotState.current_task_id` asymmetry | Open — accepted asymmetry for now |
| `get_eligible_robots` 6-parameter signature | Open — not a blocker, but a candidate for bundling |
