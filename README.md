# Core Design

## Two main services

**Assignment service** — owns which robot is assigned to which task.

**Store service** — owns robot/task definitions and runtime state.

The simulation reads assignments and applies them to the current state each tick. It writes the resulting state back to the store. It does not decide when to stop or reassign — that is not its job. It is a dumb applicator and state updater.

The LLM reads from the store and writes assignments via the assignment service.

Views are stateless renderers. They only know how to display a `SimulationState`. Given the full sequence of states across all ticks, you can replay any run.

## Running experiments

Scenarios, robots, and tasks are defined per-experiment. Run them via:

```
python -m experiments.run scenario_01/baseline --model gpt-4o
```

Outputs are written to:

```
experiments/<scenario>/<override_variant>/runs/<model>-<date>/
    artifacts/   ← per-tick service state (registry, state, assignments JSON)
    results.json ← aggregated simulation + LLM results
```

## Analysis

The simulation is the source of truth for hard facts. Each tick produces a `StepOutcome` containing events like task completions and robot state changes. These are aggregated into a `SimulationAnalysis` at the end of each run.

The LLM agent tracks tokens in, tokens out, tool calls, and latency per invocation. These are aggregated into an `AgentAnalysis` at the end of each run.

Both are written to `results.json` and form the measurable data for the experiment.
