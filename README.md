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

**Scenario files:** `scenarios/warehouse_mega.json`, `scenarios/warehouse_full_feature.json` 

**Example scenario shape:** `scenarios/example_scenario_shape.json`

---

## Development

| Command | Description |
| ------------ | --------------------------------- |
| `make test` | Run all tests |
| `make lint` | Check import layer boundaries |
| `make check` | Run lint + tests |

---