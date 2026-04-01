"""
experiments/run.py

Entrypoint for running a single experiment.

Usage (from repo root):
    python -m experiments.run <scenario> <override_variant> <model>

Example:
    python -m experiments.run scenario_01 baseline gpt-4o
    python -m experiments.run scenario_01 structured_override gpt-4o

Outputs artifacts and results.json into:
    experiments/<scenario>/<override_variant>/runs/<model>-<timestamp>/
"""

import asyncio
import importlib
import json
import sys
from datetime import datetime
from pathlib import Path

from simulation import JsonAssignmentService, JsonSimulationStore, SimulationRunner
from app.agents import ASI1_AGENT, GPT4O_AGENT, GEMINI_AGENT, CLAUDE_AGENT

MAX_TICKS = 100

MODEL_REGISTRY = {
    "gpt-4o":           GPT4O_AGENT,
    "gemini-2.0-flash": GEMINI_AGENT,
    "claude-haiku":     CLAUDE_AGENT,
    "asi1":             ASI1_AGENT,
}

EXPERIMENTS_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# 1. Validation
# ---------------------------------------------------------------------------

def validate_run(scenario: str, override_variant: str, model: str) -> None:
    defn_dir = EXPERIMENTS_DIR / scenario / "definition"
    for required in ("robots.py", "tasks.py", "environment.py"):
        if not (defn_dir / required).exists():
            raise SystemExit(f"missing {defn_dir / required}")

    rules_path = EXPERIMENTS_DIR / scenario / override_variant / "rules.md"
    if not rules_path.exists():
        raise SystemExit(f"missing rules.md at {rules_path}")

    if model not in MODEL_REGISTRY:
        valid = ", ".join(MODEL_REGISTRY)
        raise SystemExit(f"unknown model '{model}'. valid: {valid}")


# ---------------------------------------------------------------------------
# 2. Load scenario definition
# ---------------------------------------------------------------------------

def load_definition(scenario: str):
    base = f"experiments.{scenario}.definition"
    robots_mod = importlib.import_module(f"{base}.robots")
    tasks_mod  = importlib.import_module(f"{base}.tasks")
    env_mod    = importlib.import_module(f"{base}.environment")

    for mod, names in (
        (robots_mod, ("ROBOTS", "ROBOT_STATES")),
        (tasks_mod,  ("TASKS",  "TASK_STATES")),
        (env_mod,    ("ENVIRONMENT",)),
    ):
        for name in names:
            if not hasattr(mod, name):
                raise SystemExit(f"{mod.__name__} is missing '{name}'")

    return (
        robots_mod.ROBOTS,
        robots_mod.ROBOT_STATES,
        tasks_mod.TASKS,
        tasks_mod.TASK_STATES,
        env_mod.ENVIRONMENT,
    )


# ---------------------------------------------------------------------------
# 3. Create run output directory
# ---------------------------------------------------------------------------

def make_run_dir(scenario: str, override_variant: str, model: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = EXPERIMENTS_DIR / scenario / override_variant / "runs" / f"{model}-{timestamp}"
    (run_dir / "artifacts").mkdir(parents=True)
    return run_dir


# ---------------------------------------------------------------------------
# 4. Wire simulation services and agent
# ---------------------------------------------------------------------------

def wire_services(robots, robot_states, tasks, task_states, environment, artifacts_dir: Path, model: str):
    assigner = JsonAssignmentService(artifacts_dir / "assignments.json")
    store = JsonSimulationStore(
        registry_path=artifacts_dir / "registry.json",
        state_path=artifacts_dir / "state.json",
        assignment_service=assigner,
    )

    for robot_id, robot in robots.items():
        store.add_robot(robot, robot_states[robot_id])
    for task_id, task in tasks.items():
        store.add_task(task, task_states[task_id])

    runner = SimulationRunner(
        environment=environment,
        store=store,
        assignment_service=assigner,
    )

    # TODO: inject override_variant rules.md into agent system prompt
    agent = MODEL_REGISTRY[model](store, assigner)

    return runner, agent


# ---------------------------------------------------------------------------
# 5. Simulation loop
# ---------------------------------------------------------------------------

def run_loop(runner, agent) -> None:
    def invoke(prompt: str) -> None:
        asyncio.run(agent.invoke(prompt, max_tool_calls=5))

    invoke("Simulation started. Assign all robots to tasks.")

    for _ in range(MAX_TICKS):
        _, outcome = runner.step()
        if outcome.tasks_spawned or outcome.tasks_completed:
            invoke("Tasks changed. Reassign robots as needed.")


# ---------------------------------------------------------------------------
# 6. Write results
# ---------------------------------------------------------------------------

def write_results(runner, agent, results_path: Path) -> None:
    sim  = runner.stop()
    llm  = agent.get_analysis()

    results = {
        "simulation": {
            "total_ticks":      sim.total_ticks,
            "makespan":         sim.makespan,
            "tasks_completed":  sim.tasks_completed,
            "tasks_failed":     sim.tasks_failed,
        },
        "agent": {
            "total_calls":      llm.total_calls,
            "total_tokens_in":  llm.total_tokens_in,
            "total_tokens_out": llm.total_tokens_out,
            "mean_latency_ms":  llm.mean_latency_ms,
            "min_latency_ms":   llm.min_latency_ms,
            "max_latency_ms":   llm.max_latency_ms,
            "mean_tool_rounds": llm.mean_tool_rounds,
        },
    }

    results_path.write_text(json.dumps(results, indent=2))
    print(f"results written to {results_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: python -m experiments.run <scenario> <override_variant> <model>")

    _, scenario, override_variant, model = sys.argv

    validate_run(scenario, override_variant, model)

    robots, robot_states, tasks, task_states, environment = load_definition(scenario)
    run_dir = make_run_dir(scenario, override_variant, model)
    runner, agent = wire_services(
        robots, robot_states, tasks, task_states, environment,
        run_dir / "artifacts",
        model,
    )

    run_loop(runner, agent)
    write_results(runner, agent, run_dir / "results.json")


if __name__ == "__main__":
    main()
