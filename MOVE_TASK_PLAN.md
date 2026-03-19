# MoveTask Implementation Plan

Robots collectively carry a task object from its current position to a destination.
The task + eligible robots form a **rigid body formation** that moves as one unit each tick.

---

## Phase 1 — Domain types (`simulation/domain/move_task.py`)

**What:**
- `MoveTask(BaseTask)` with `destination: Position`, `min_robots_required: int`, `min_distance: int`
  - `min_distance`: max Manhattan distance a robot can be from `current_position` to count as eligible
- `MoveTaskState(BaseTaskState)` with `current_position: Position`

No tests — pure dataclasses, behavior is covered by Phase 4 observer tests.

---

## Phase 2 — Formation planner (`simulation/algorithms/formation_planner.py`)

**What:**
Two pure functions. No task/robot/state domain knowledge — only `Position`, `Environment`, `frozenset[Position]`.

```
is_formation_clear(
    positions: Iterable[Position],
    environment: Environment,
    occupied: frozenset[Position],
) -> bool
```
Returns `True` if every position is in-bounds, not an obstacle, and not in `occupied`.

```
plan_formation_move(
    formation: frozenset[Position],
    destination: Position,
    environment: Environment,
    occupied: frozenset[Position],
) -> tuple[int, int] | None
```
- Tries cardinal directions that reduce Manhattan distance toward `destination`
- For each candidate `(dx, dy)`: shifts the full `formation` and calls `is_formation_clear`
- Returns first valid `(dx, dy)`, or `None` if all directions blocked

**Tests (`tests/unit/algorithms/test_formation_planner.py`):**

`plan_formation_move`:
- Clear path → returns direction toward destination
- Obstacle in the way → picks alternate direction if available
- Occupied robot blocks path → avoids it
- All directions blocked → returns None
- Formation already at destination → returns None (no move needed)
- Single-position formation (just task, no robots) → still works correctly

**Testable in isolation:** no observer/applicator dependency.

---

## Phase 3 — StepOutcome + Applicator

**What:**

`step_outcome.py`: add `tasks_moved: list[tuple[TaskId, Position]]`
- Written by Observer; consumed by Applicator
- Follows same pattern as existing `waypoints` and `rescue_points_found` fields

`applicator.py`: apply `tasks_moved` to `MoveTaskState.current_position`
- Before the "mark completed tasks" block (position must be up-to-date before completion is stamped)
- `dataclasses.replace(existing, current_position=new_position)`

**Tests (`tests/unit/engine_rewrite/test_applicator.py` additions):**
- `tasks_moved` with a valid `MoveTaskState` → `current_position` advances
- `tasks_moved` + `tasks_completed` in same outcome → state has new position AND `status=DONE`

**Testable in isolation:** construct a `StepOutcome` with `tasks_moved` populated manually, call `apply_outcome`, assert on resulting `MoveTaskState`. No observer needed.

---

## Phase 4 — Observer (`simulation/engine_rewrite/observer.py`)

**What:** Three changes to `classify_step`.

**`_goal_for` update:**
Add `isinstance(task, MoveTask)` branch → return `task_state.current_position`.
Robots navigate toward the task's current position via normal pathfinding.
Robots already within `min_distance` produce `intended_move = None` naturally (already at goal) → they become stayers in `resolve_collisions`.

**Pass 3 update:**
Add `isinstance(task, MoveTask)` branch:
- Skip work logic (not a `WorkTask`)
- If `effective_position.manhattan(task_state.current_position) <= task.min_distance` → add robot to `eligible_by_task[task_id]`

**Pass 3.5 (new, after Pass 3):**
For each MoveTask where `len(eligible_by_task[task_id]) >= task.min_robots_required`:
- Build `formation = frozenset({task_state.current_position} | {eligible robot effective positions})`
- Build `occupied = frozenset` of resolved positions for all robots NOT in this formation
- Call `plan_formation_move(formation, task.destination, state.environment, occupied)`
- If `(dx, dy)` returned:
  - Append `(task_id, new_task_position)` to `outcome.tasks_moved`
  - Append `(robot_id, new_robot_position)` to `outcome.moved` for each eligible robot
  - If `new_task_position == task.destination`: append `task_id` to `outcome.tasks_completed`

**Tests (`tests/unit/engine_rewrite/test_move_task.py`):**
- Robot far from task → navigates toward `current_position`, task does not move
- Robot within `min_distance` → eligible; robot outside → not eligible
- Eligible count `< min_robots_required` → formation does not move
- Eligible count `>= min_robots_required` → task and all eligible robots shift by `(dx, dy)`
- Formation blocked by environment obstacle → stays put
- Formation blocked by another robot → stays put
- Task reaches `destination` → `tasks_completed` populated
- Full round-trip: `classify_step` + `apply_outcome` → `MoveTaskState.current_position` updated, robot positions updated, completion stamped

---

## Commit plan

One commit per phase:
- `feat: add MoveTask and MoveTaskState domain types`
- `feat: add formation_planner — is_formation_clear and plan_formation_move`
- `feat: add tasks_moved to StepOutcome; apply in Applicator`
- `feat: wire MoveTask into Observer — goal routing, eligibility, formation move pass`
