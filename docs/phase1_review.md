# Phase 1 Review — Readability

All instances where code does something non-obvious from a domain perspective,
with a suggestion for each.

---

## observer.py

### 1. Silent drop for unknown task/robot references

```python
if None in (task, task_state, robot, robot_state):
    continue
```

**What it actually means:** an assignment that references a task or robot not
present in the current simulation state is silently discarded. This is a real
event (stale assignment, out-of-sync assigner) but produces no trace in the outcome.

**Fix:** give it an `IgnoreReason` (e.g. `UNKNOWN_ENTITY`) and append to
`assignments_ignored` so it appears in the outcome like every other invalid assignment.

---

### 2. "Last assignment wins" is a hidden dict overwrite

```python
robot_to_task = {a.robot_id: a.task_id for a in assignments}
...
if robot_to_task.get(assignment.robot_id) != assignment.task_id:
    continue
```

**What it actually means:** if a robot appears in the assignment list more than once,
only the last entry is used. The rule is real but the mechanism — a dict comprehension
that silently overwrites duplicates, then a skip check — reads like a filter with no
obvious relationship to deduplication.

**Fix:** deduplicate explicitly before the main loop with a named step:

```python
# Later assignment supersedes earlier ones for the same robot.
active_assignments = {a.robot_id: a for a in assignments}.values()
```

---

### 3. `None` in `intended_moves` means two different things

```python
intended_moves[assignment.robot_id] = None  # used when robot stays in place
```

`None` is used to mean both "robot has no move this tick" and "robot is a stayer
that blocks other movers." The collision resolver then re-derives stayer vs mover
from whether the value is `None`. Two distinct states sharing one sentinel.

**Fix:** use an explicit type:

```python
@dataclass
class IntendedMove:
    destination: Position | None  # None = stay in place
```

---

### 4. `assert isinstance` used as type narrowing, not correctness checking

```python
assert isinstance(task, Task)
if _robot_can_work(task, effective_position, state):
    ...
```

```python
assert isinstance(task, Task) and isinstance(task_state, TaskState)
new_work_ticks = task_state.work_done.tick + len(workers)
```

These asserts are doing type narrowing for the type checker, not catching bugs.
If a third task type is ever added, the assert passes and the code silently falls
through into logic that doesn't apply to it.

**Fix:** use `isinstance` as a proper conditional:

```python
if not isinstance(task, Task):
    raise TypeError(f"expected Task, got {type(task)}")
```

Or restructure the passes so each one explicitly handles only the task types it
knows about, rather than asserting the world is what it expects.

---

### 5. `len(workers)` as "work contributed this tick"

```python
new_work_ticks = task_state.work_done.tick + len(workers)
if new_work_ticks >= task.required_work_time.tick:
    outcome.tasks_completed.append(task_id)
```

**What it actually means:** each robot working on a task this tick contributes
exactly 1 tick of work progress. `len(workers)` is being used as that count.

**Fix:** name the intent:

```python
work_contributed_this_tick = len(workers)  # each robot contributes 1 tick of progress
```

---

### 6. `.tick` unwrapping to do arithmetic on `Time`

```python
task_state.work_done.tick + len(workers)
...
task.required_work_time.tick
```

`Time` is a domain wrapper but the code reaches inside it (`.tick`) to do raw
integer arithmetic. This means `Time` is providing no abstraction benefit here.

**Fix:** either give `Time` the operators it needs (`__add__`, `__ge__`, etc.)
so callers never touch `.tick`, or remove `Time` as a wrapper and use `int` directly.
The current state is the worst of both worlds.

---

### 7. `break` encodes a one-discovery-per-robot-per-tick rule

```python
for rescue_point in state.environment.rescue_points.values():
    ...
    if effective_position == rescue_point.position:
        outcome.rescue_points_found.append(...)
        break  # <-- business rule hidden here
```

**What it actually means:** a robot can discover at most one rescue point per tick,
even if it somehow occupies a position shared by multiple rescue points.

**Fix:** move the `break` out by making the rule explicit before the loop:

```python
# A robot can discover at most one rescue point per tick.
undiscovered = [rp for rp in ... if not already_found and not seen_this_tick]
first_match = next((rp for rp in undiscovered if effective_position == rp.position), None)
if first_match:
    ...
```

---

### 8. Magic priority `10` for spawned rescue tasks

```python
return Task(
    ...
    priority=10,
    ...
)
```

**What it actually means:** rescue tasks are always assigned the highest priority
in the system. The number `10` is a magic constant with no named home.

**Fix:** define a named constant close to where task priorities are defined:

```python
RESCUE_TASK_PRIORITY = 10  # rescue tasks are highest priority
```

---

### 9. Observer should not be generating task IDs at all

```python
new_task_id = TaskId(max(state.tasks.keys(), default=0) + 1)
```

The Observer is a pure function — it classifies what happens this tick. Minting
a new `TaskId` requires knowledge of the existing ID space, which is an
infrastructural concern, not a business rule. The Observer shouldn't own this.

**Fix:** `tasks_spawned` in `StepOutcome` should carry specs, not fully-formed tasks:

```python
@dataclass
class RescueTaskSpec:
    rescue_point_id: RescuePointId
    position: Position
    required_work_time: Time
    min_robots_needed: int
```

The Observer emits `RescueTaskSpec` objects. The runner reads them, assigns IDs,
constructs the `Task` objects, and writes them to the `TaskRegistry`. ID generation
moves out of the engine entirely, where it belongs.

---

## applicator.py

### 10. Task completion is recorded one tick after it actually happened

```python
new_time = state.t_now + Time(1)
...
new_task_state.completed_at = new_time  # wrong — completion happened at t_now
```

The work that caused completion happened at `state.t_now`. But `completed_at` is
set to `state.t_now + 1`. Meanwhile `started_at` correctly uses `state.t_now`.
A task that starts and completes in the same tick ends up with `started_at=0,
completed_at=1`, which is incorrect.

**Fix:** `completed_at` should use `state.t_now`, the same reference as `started_at`.
`new_time` (`t_now + 1`) is only needed for advancing the simulation clock on the
returned state — it should not be reused for recording when domain events occurred:

```python
new_task_state.completed_at = state.t_now  # completed during this tick
```

---

### 12. Work tick counting via `dict.get(..., 0) + 1`

```python
work_ticks_by_task[task_id] = work_ticks_by_task.get(task_id, 0) + 1
```

**What it actually means:** each entry in `outcome.worked` is one robot-tick of
work on a task, so this is counting how many robots worked on each task this tick.

**Fix:** use `collections.Counter` and name the variable to reflect the domain:

```python
robots_working_per_task = Counter(task_id for _, task_id in outcome.worked)
```

---

### 13. Intermediate dict for spawned task states serves no purpose

```python
new_task_states_for_spawned: dict[TaskId, TaskState] = {}
for task in outcome.tasks_spawned:
    new_tasks[task.id] = task
    new_task_states_for_spawned[task.id] = TaskState(task_id=task.id)
new_task_states.update(new_task_states_for_spawned)
```

The intermediate dict `new_task_states_for_spawned` is built only to be merged
into `new_task_states` immediately after. It adds no clarity.

**Fix:** write directly into `new_task_states` in the loop:

```python
for task in outcome.tasks_spawned:
    new_tasks[task.id] = task
    new_task_states[task.id] = TaskState(task_id=task.id)
```

---

### 14. `rescue_found` uses bare `True` as the "found" sentinel

```python
rescue_found={**task_state.rescue_found, rescue_point_id: True}
```

`True` is the value that means "this rescue point has been found." A `dict[RescuePointId, bool]`
with `True/False` values is essentially a set with extra steps, and reads as
`rescue_found[rp_id]` which sounds like a question, not a fact.

**Fix:** replace the dict with a plain set:

```python
rescue_found: set[RescuePointId]  # IDs of rescue points confirmed found
```

Membership check (`rp_id in rescue_found`) is clearer than `rescue_found.get(rp_id, False)`.
