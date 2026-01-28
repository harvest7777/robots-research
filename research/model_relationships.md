## Purpose of this file

This document defines the **minimal interaction contract** between simulation models (Environment, Robots, Tasks, Workload, Coordinator) for **Option C: distributed task allocation**.
It is intentionally simple: it specifies **what reads/writes what** and **when** during the simulation loop.

## Core Models (and who “owns” state)

- **Environment** (owns geometry): bounds, obstacles, named locations (zones/stations).
- **Task** (owns job state): requirements, timing, assignment status, progress.
- **Robot** (owns agent state): position, speed, capabilities, current action/task.
- **Workload** (owns task creation): generates new Tasks over time (or fixed set at \(t=0\)).
- **Coordinator / Allocator** (owns decision logic): computes task↔robot assignments.
- **Simulation Engine** (owns the clock + orchestration): applies updates in a consistent order; logs metrics.

## Data Flow (what each model reads/writes)

## What researchers implement/test (explicit)
Researchers primarily implement/test the **Coordinator / Allocator policy** (i.e., the coordination strategy):
- **Reactive** (nearest-feasible)
- **Centralized** (greedy / matching)
- **Market-based** (auction / contract-net)
- **Hierarchical** (cluster + leader assignment)

The simulation engine stays fixed and is responsible for applying assignments, simulating motion through obstacles, executing tasks, and logging metrics.

## Assignment object (Coordinator output)
An `Assignment` is a **pure data record** returned by the Coordinator. The Simulation Engine applies it.
- **Required fields**:
  - `robot_id`: which robot should take the task
  - `task_id`: which task to assign
  - `assigned_time_s`: current simulation time (for auditing/metrics)
- **Optional fields** (only if needed):
  - `path`: list of grid cells/waypoints the robot plans to follow (useful for visualization/debug; not required for v1)

### Environment

- **Read by**:
  - Robots (distance/path feasibility to targets)
  - Coordinator (cost estimates like travel time)
  - Workload (valid placement of tasks)
- **Writes**: none during runtime (static after initialization).

### Workload → Tasks

- **Produces**: new `Task` objects (id/type/location/requirements/duration/etc.).
- **Writes**:
  - adds tasks to the simulation’s task list / event queue
  - sets `task.arrival_time`
- **Does not** assign tasks to robots (that is the Coordinator’s job).

### Coordinator (Allocator)

- **Reads**:
  - robot snapshots: `{pos, speed, capabilities, status, current_task}`
  - task snapshots: `{status, location, requirements, priority/deadline (optional)}`
  - environment distance/path cost
  - communication constraints (optional; for distributed variants)
- **Writes**: none directly (Coordinator is pure).
- **Produces**: `list[Assignment]`
- **Hard rule**: Coordinator does not move robots or advance task progress; it only proposes assignments.

### Simulation Engine (applies assignments)
- **Reads**: `list[Assignment]`
- **Writes**:
  - `task.status`: `unassigned -> assigned`
  - `task.assigned_robot_id`
  - `robot.current_task_id` and `robot.status` (e.g., `moving`)

### Robots (execution)

- **Reads**:
  - assigned task id + task location/duration
  - environment distance/path feasibility
- **Writes**:
  - `robot.pos` (movement over time)
  - `robot.status` (idle/moving/executing)
  - task progress signals (via Simulation Engine), e.g. “arrived”, “execution time consumed”

### Tasks (lifecycle)

- **Read by**:
  - Coordinator (to assign)
  - Robots (to execute)
  - Metrics logger
- **Written by**:
  - Workload (creation, arrival time)
  - Coordinator (assignment fields)
  - Simulation Engine (state transitions + timestamps + progress)

## Simulation Loop (minimal update order)

At each time step \(t \to t+\Delta t\):

1. **Workload step**: create any newly arrived tasks; mark them `unassigned`.
2. **Coordinator step**: for idle robots and unassigned tasks, compute assignments.
3. **Robot motion step**: move each robot toward its assigned task location (if any).
4. **Task execution step**:
   - if robot is at task location, decrement remaining task duration
   - when duration reaches 0: mark task `done`, set completion time, set robot `idle`
5. **Metrics step**: log makespan-in-progress, completion times, travel distance, etc.

## Minimal Interface Contracts (recommended)

- **Environment**
  - `distance(a_pos, b_pos) -> float`
  - `is_path_free(a_pos, b_pos) -> bool`
- **Workload**
  - `spawn_tasks(t_now) -> list[Task]`
- **Coordinator**
  - `assign(t_now, robots, tasks, env) -> list[Assignment]`
- **Robot**
  - `can_execute(task) -> bool`
  - `step(dt, env, tasks) -> None` (updates robot state only)

## First implementation simplification (v1)

- No comm modeling: Coordinator has global visibility (even if the _policy_ is “distributed-style” later).
- Obstacles are required: v1 uses a **simple grid** + **simple pathing cost**.
  - Minimum acceptable: compute cost using **grid shortest path** (e.g., BFS for unweighted grids) so blocked cells matter.
- No dependencies/team tasks/battery initially: add later without changing the interaction contract above.
