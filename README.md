# Multi-robot coordination simulation

## Run the simulation

```bash
python main.py <scenario> [--renderer {terminal,mujoco}]
```

| Argument     | Description                                                  |
| ------------ | ------------------------------------------------------------ |
| `scenario`   | Path to scenario JSON (e.g. `scenarios/warehouse_mega.json`) |
| `--renderer` | `terminal` (default) or `mujoco`                             |

**Examples**

```bash
python main.py scenarios/warehouse_mega.json --renderer terminal
python main.py scenarios/warehouse_mega.json --renderer mujoco
```

With MuJoCo’s Python environment: use `mjpython` instead of `python` when using `--renderer mujoco`.

**Scenario files:** `scenarios/warehouse_mega.json`, `scenarios/warehouse_full_feature.json`, `scenarios/example_scenario_shape.json`

---

## Architecture

- **`main.py`** — Entry point: parses CLI, loads scenario, wires assignment/pathfinding, runs sim loop with chosen renderer.

- **`scenario_loaders/`** — Loads JSON into a `Simulation`: environment (grid, zones, obstacles), robots, tasks, robot_states, task_states.

- **`simulation_models/`** — Core types: `Environment`, `Robot`, `Task`, `RobotState`, `TaskState`, `Simulation`, `SimulationSnapshot`, `Assignment`. `Simulation` holds state and drives `step()`; assignment and pathfinding are pluggable callables.

- **`coordinator_algorithms/`** — Assignment: e.g. `simple_assign(tasks, robots) → list[Assignment]`.

- **`pathfinding_algorithms/`** — Pathfinding: e.g. `astar_pathfind(env, start, goal, occupied) → next position or None`.

- **`simulation_view/`** — Rendering: `SimulationView` builds frames from a snapshot; `TerminalRenderer` or `MuJoCoRenderer` display them.

- **`mcp_server/`** — MCP server for LLM-in-the-loop evaluation (simulation + metrics).
