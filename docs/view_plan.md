# View Refactor Plan (Phase 4)

## Motivation

The current `SimulationView` is a single class that:
- Takes `SimulationSnapshot` (old engine) — incompatible with the new `SimulationState`
- Mixes rendering logic, symbol constants, and computation in one file
- Writes directly into a `Frame` at specific row offsets, making each section
  impossible to test in isolation
- Has explicit TODOs calling out the same problems (lines 63, 216–223 in
  `simulation_view.py`)

The old view stays alive until `main_v2.py` is wired up (Phase 6). The new view
lives in `simulation_view/v2/` alongside it.

---

## Core Design Decision

Each section of the display becomes a **pure function returning `list[str]`**
(lines of text). A thin assembler stamps them into a `Frame`.

```
render_header(state)      -> list[str]   # tick, assignment summary
render_environment(state) -> list[str]   # 2D grid, one string per row
render_robots(state)      -> list[str]   # robot list with pos/battery
render_tasks(state)       -> list[str]   # task list with status/progress
render_activity(state)    -> list[str]   # per-robot what they're doing
render_rescue_points(state) -> list[str] # rescue point discovery status
```

**Why `list[str]` and not direct Frame writes:**
- Each panel is testable in isolation: `assert any("100%" in l for l in render_robots(state))`
- Panels have no knowledge of their row position — the assembler owns layout
- Adding, removing, or reordering sections requires no changes to panel code

**What the assembler does:**
```python
class SimulationViewV2:
    def render(self, state: SimulationState, width: int, height: int) -> Frame:
        frame = make_frame(width, height)
        row = 0
        for section in [render_header(state), [""], render_environment(state), ...]:
            for line in section:
                stamp(frame, row, 0, line)
                row += 1
        return frame
```

The assembler skips sections gracefully if `row >= len(frame)` (terminal too small).

---

## Component Contracts

| Component | Contract |
|---|---|
| `symbols.py` | All display constants and pure symbol-derivation functions; no domain logic, no imports from engine. |
| `panels/header.py` | Given state, returns lines showing current tick and one line per assignment. |
| `panels/environment.py` | Given state, returns one string per grid row with robots, obstacles, task targets, work areas, rescue points, and zones overlaid. |
| `panels/robots.py` | Given state, returns one line per robot showing id, position, and battery level. |
| `panels/tasks.py` | Given state, returns one line per task showing status symbol, label, priority, and progress (work-based or discovery-based). |
| `panels/activity.py` | Given state, returns one line per robot describing its current assignment or idle status. |
| `panels/rescue_points.py` | Given state, returns one line per rescue point showing name, position, and found/unfound status. Only rendered when rescue points exist in the environment. |
| `view.py` (`SimulationViewV2`) | Assembler only — calls panels, stamps lines into a Frame, handles row overflow; no rendering logic of its own. |

---

## Input

All panels take only `SimulationState`. No separate assignments parameter —
`state.assignments` carries the current assignment snapshot.

```python
SimulationState:
    environment    # grid dimensions, obstacles, zones, rescue_points
    robots         # immutable robot definitions (capabilities, speed)
    robot_states   # position, battery_level per robot
    tasks          # task definitions
    task_states    # work progress, status per task (lazy — absent until first work tick)
    assignments    # tuple[Assignment, ...] — current robot-to-task bindings
    t_now          # current tick
```

---

## File Layout

```
simulation_view/
    frame.py                  ← unchanged (shared)
    terminal_renderer.py      ← unchanged (shared)
    mujoco_renderer.py        ← unchanged (shared)
    simulation_view.py        ← OLD — keep alive until Phase 6
    v2/
        __init__.py
        symbols.py
        panels/
            __init__.py
            header.py
            environment.py
            robots.py
            tasks.py
            activity.py
            rescue_points.py
        view.py
```

---

## symbols.py

Extracted from the current `simulation_view.py`. Contains:

```python
# Constants
ROBOT_SYMBOL         = "R"
OBSTACLE_SYMBOL      = "#"
TASK_AREA_SYMBOL     = "+"
RESCUE_POINT_SYMBOL  = "^"
EMPTY_SYMBOL         = "."

ZONE_SYMBOLS:          dict[ZoneType, str]    # I, M, L, X, C
TASK_TYPE_LABELS:      dict[TaskType, str]    # RI, AI, PM, ER, PU, --
TASK_TYPE_FULL_NAMES:  dict[TaskType, str]

# Pure functions
def task_label(task: BaseTask) -> str           # SR for SearchTask, type label otherwise
def task_full_name(task: BaseTask) -> str
def task_status_symbol(state: BaseTaskState) -> str   # ●, ✗, ◑, ○
def task_id_symbol(task_id: TaskId) -> str            # "1"–"9", "*" for ≥10
```

---

## Key Differences from the Old View

| Old | New |
|---|---|
| Takes `SimulationSnapshot` | Takes `SimulationState` |
| `snapshot.active_assignments` — old `Assignment` with `robot_ids: frozenset` | `state.assignments` — flat `Assignment(task_id, robot_id)` tuples |
| `rescue_found: dict[TaskId, bool]` — `.values()` iteration | `rescue_found: frozenset[TaskId]` — `rp.id in state.rescue_found` |
| Section renderers are methods that write into Frame | Panels are pure functions returning `list[str]` |
| Symbol constants and logic mixed into the view file | Extracted to `symbols.py` |
| `_compute_task_work_areas` is a method with `self` access | Pure function in `environment.py` taking explicit args |
| One class, one file, untestable in isolation | One file per panel, each independently testable |

---

## Testability Pattern

```python
# tests/unit/view_v2/test_robots_panel.py

def test_shows_battery_as_percentage():
    state = _state_with_robot(battery=0.5)
    lines = render_robots(state)
    assert any("50%" in line for line in lines)

def test_shows_robot_position():
    state = _state_with_robot(position=Position(3, 7))
    lines = render_robots(state)
    assert any("3" in line and "7" in line for line in lines)
```

No Frame construction, no row counting, no ANSI codes in tests.

---

## Implementation Order

1. `symbols.py` — pure constants and helpers, no dependencies on panels
2. `panels/environment.py` — most complex, test the grid logic first
3. `panels/robots.py`, `panels/tasks.py`, `panels/activity.py`, `panels/header.py`,
   `panels/rescue_points.py` — straightforward, one commit each
4. `view.py` — assembler, wires panels together
5. Unit tests for each panel as it's written

---

## What Stays Unchanged

- `frame.py` — `Frame`, `make_frame`, `stamp`, `frame_to_string` are reused as-is
- `terminal_renderer.py` — takes a `Frame`, works with any view that produces one
- `mujoco_renderer.py` — untouched

The `TerminalRenderer` + `Frame` contract is the right abstraction boundary.
`SimulationViewV2` produces a `Frame`; the renderer consumes it. Nothing changes
on the renderer side.
