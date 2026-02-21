# Implementation Plan — Next Steps

## Goal (stay aligned)

**We are building an LLM-in-the-loop multi-robot coordination evaluator:** the simulation will run on an MCP server; an LLM produces task-assignment decisions (e.g. who does which task, or how to coordinate object moves); we run the simulation with those decisions and return metrics (battery, throughput, makespan, etc.) so the LLM can judge and improve its coordination strategy. A core requirement from the professor is **coordinating movement of an object**—i.e. robots physically moving/relaying an object (pick, carry, hand off, deliver)—not only “robot goes to task location and makes progress in place.”

---

## Next steps (concise)

### 1. Object-move coordination (professor requirement)

- **Extend the task/model** so some tasks involve **moving an object** (e.g. from A → B), not just working at a fixed location.
- **Define object state**: e.g. `object_id`, `position`, `carried_by_robot_id | None`, `goal_position` (and optionally waypoints / handoff points).
- **Extend robot behavior**: pick up at object location, carry (object position = robot position), drop or hand off at target or to another robot; optional “handoff” tasks for multi-robot relay.
- **Extend Coordinator/Assignment**: assignments can include “move object X to Y” or “hand off object X to robot R” (and which robot picks up, which receives), so the LLM can reason about object flow, not only which robot does which location-based task.
- **Simulation loop**: add steps for object state updates (e.g. after robot motion: update object position if carried; resolve handoffs when robots are adjacent).

### 2. Metrics for the LLM

- **Implement and expose** (for MCP/LLM consumption): **battery** (e.g. min/mean/final per robot or fleet), **task throughput** (tasks completed per time), **makespan** (time until last task done), and optionally travel distance, idle time, failed tasks.
- **Single structured response** (e.g. JSON) per run: run id, scenario summary, metrics dict, optional per-robot/per-task breakdown so the LLM can attribute performance to decisions.

### 3. MCP server for simulation

- **Host the simulation behind an MCP server**: one or more tools, e.g. “run_simulation(scenario_id_or_config, assignment_policy_or_decisions, max_steps?)” that runs the sim and returns the metrics payload.
- **Contract**: inputs = scenario (or reference) + LLM-produced assignments/decisions; output = metrics + optional trace (e.g. event log or key frames) for debugging.
- **Keep the current sim as the engine**: same loop (workload → coordinator → motion → task/object execution → metrics); MCP layer only invokes it and formats results.

### 4. LLM-facing contract

- **Define the assignment/decision format** the LLM must produce (e.g. list of assignments, or high-level “object X: robot R1 picks up, robot R2 receives at zone Z”) so it’s easy to parse and feed into the simulation.
- **Document** required metrics and their meanings so the LLM prompt can ask for “efficient” behavior (battery, throughput, makespan) and interpret the numbers.

### 5. Order of work (suggested)

1. **Object model + move coordination** in the sim (task types, object state, pick/carry/drop or handoff, coordinator output format for object moves).
2. **Metrics aggregation** (battery, throughput, makespan) and a single “run result” structure.
3. **MCP server** that accepts scenario + decisions and returns that run result.
4. **LLM contract doc** and example prompts so the loop (LLM → MCP run → metrics → LLM) is clear and reproducible.

---

*Preface: any feature or refactor should be checked against the goal above—LLM-driven coordination evaluation, with object-moving coordination and metrics over MCP—so we don’t drift into unrelated work.*
