## Milestone 1.1 — Scenario Selection (Chosen: Option C)

### Selected Scenario

**Option C: Distributed Task Allocation (Heterogeneous Fleet)**

### Explicit Criteria (What Option C Requires)

- **Fleet is heterogeneous**: robots have **different capability sets** and **different speeds/constraints** (e.g., Inspector vs Repair vs Data Collector).
- **Tasks are heterogeneous**: tasks have **types**, **locations**, and **capability requirements** (a task is feasible only for robots whose capabilities satisfy it).
- **Dynamic allocation is core**: the system must decide **which robot does which task** (and when), rather than only moving robots.
- **Multi-robot interaction exists through coordination**: robots may coordinate **centrally** or **distributedly** (e.g., bidding/auction), optionally under communication limits.
- **Performance is measurable**: you can compute at least **completion time** metrics (e.g., makespan, average task completion time), and optionally travel/energy/communication overhead.

### Models (Real World → Code Representation)

#### 1) Environment Model

- **Real world**: warehouse floor layout where robots travel to zones/stations; obstacles may block motion.
- **Code**:
  - **State**: 2D bounds; **occupancy grid** (free/blocked); locations of zones and stations.
  - **APIs/Fields**:
    - `distance(a, b)` (Euclidean or Manhattan)
    - `is_free(x, y)` / `is_path_free(a, b)`
    - `zones[]`, `stations[]` (positions) (future)

#### 2) Robot Model (Agent)

- **Real world**: individual robot with a position, motion speed, and equipment (capabilities); may be busy executing a job.
- **Code**:
  - **State (minimum)**:
    - `id`
    - `pos = (x, y)`
    - `speed_mps`
    - `capabilities = { ... }`
    - `status ∈ {idle, moving, executing}`
    - `current_task_id | None`
  - **Optional (later)**:
    - `battery_pct`, `battery_drain_move`, `battery_drain_idle`
    - `comm_range_m`
    - `task_queue[]`
  - **Methods**:
    - `can_execute(task) -> bool` (capability + battery feasibility if modeled)
    - `move_toward(target_pos, dt)` (simple kinematics)
    - `work_on_task(dt)` (progress timer)

#### 3) Task Model (Job)

- **Real world**: a job request at a location (inspect/diagnose/repair) requiring specific equipment and taking time to complete.
- **Code**:
  - **State (minimum)**:
    - `id`
    - `type` (e.g., routine_inspection, anomaly_investigation, preventive_maintenance, emergency_response)
    - `location = (x, y)`
    - `required_capabilities = { ... }`
    - `duration_est_s`
    - `status ∈ {unassigned, assigned, in_progress, done, failed}`
  - **Optional (later)**:
    - `priority` / `utility`
    - `deadline_s` (soft/hard)
    - `dependencies[]` (DAG)
    - `num_robots_required` / team requirements

#### 4) Workload / Arrival Model

- **Real world**: jobs appear over time due to operations (routine demand + occasional emergencies).
- **Code**:
  - **Minimum v1**: fixed task list generated at `t=0`.
  - **Next**: stochastic arrivals (e.g., Poisson with rate `lambda_tasks_per_min`), plus task-type mixture.

#### 5) Coordination / Allocation Model

- **Real world**: dispatching logic that decides which robot should do which job (central dispatcher, bidding, hierarchical supervisors).
- **Code**:
  - **Interface**: `assign(robots, tasks, env, t_now) -> list[Assignment]`
  - **Assignment object (what the Coordinator returns)**:
    - `robot_id`: which robot is being assigned
    - `task_id`: which task the robot should execute next
    - `assigned_time_s`: simulation time when the decision was made (for metrics/debug)
  - **Hard rule**: researchers implement this Coordinator policy; the **Simulation Engine** applies the returned `Assignment`s by mutating `Robot`/`Task` state.
  - **Minimum v1 policy**: reactive nearest-feasible assignment (or centralized greedy).
  - **Next policies**: centralized matching, auction/contract-net, hierarchical clustering.

#### 6) Time / Simulation Model

- **Real world**: system evolves continuously; robots travel, start jobs, finish jobs, and new jobs appear.
- **Code**:
  - **Discrete time step**: `dt` and `t_now`
  - Each step:
    - create arrivals (if enabled)
    - update robot motion
    - advance task execution
    - run allocation policy (when robots become idle / at fixed cadence)
    - log metrics

#### 7) Evaluation / Metrics Model

- **Real world**: how well the fleet handles demand.
- **Code (minimum)**:
  - `makespan_s`
  - `avg_task_completion_time_s` (arrival → done)
  - `total_travel_distance_m`
  - optional: `deadline_violations`, `utilization`, `messages_per_task`, `energy_used`
