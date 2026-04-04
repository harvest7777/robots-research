"""
experiments/run.py

Entrypoint for running a single experiment.

Usage (from repo root):
    python -m experiments.run <scenario>/<override_variant> --model <model>

Example:
    python -m experiments.run scenario_01/baseline --model gpt-4o
    python -m experiments.run scenario_01/structured_override --model gpt-4o

Outputs artifacts and results.json into:
    experiments/<scenario>/<override_variant>/runs/<model>-<timestamp>/
"""

import argparse
import asyncio
import importlib
import json
from datetime import datetime
from pathlib import Path

from experiments.models.task_spawn import SpawnTask
from llm.agent import AssignmentAgent
from simulation import JsonAssignmentService, JsonSimulationStore, SimulationRunner
from experiments.agents import MODEL_REGISTRY
from simulation.engine_rewrite import BaseSimulationStore
from simulation.primitives import Time

MAX_TICKS = 100

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
    tasks_mod = importlib.import_module(f"{base}.tasks")
    env_mod = importlib.import_module(f"{base}.environment")

    for mod, names in (
        (robots_mod, ("ROBOTS", "ROBOT_STATES")),
        (tasks_mod, ("TASK_SPAWNS",)),
        (env_mod, ("ENVIRONMENT",)),
    ):
        for name in names:
            if not hasattr(mod, name):
                raise SystemExit(f"{mod.__name__} is missing '{name}'")

    return (
        robots_mod.ROBOTS,
        robots_mod.ROBOT_STATES,
        tasks_mod.TASK_SPAWNS,
        env_mod.ENVIRONMENT,
    )


# ---------------------------------------------------------------------------
# 3. Create run output directory
# ---------------------------------------------------------------------------


def make_run_dir(scenario: str, override_variant: str, model: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = (
        EXPERIMENTS_DIR / scenario / override_variant / "runs" / f"{model}-{timestamp}"
    )
    (run_dir / "artifacts").mkdir(parents=True)
    return run_dir


# ---------------------------------------------------------------------------
# 4. Wire simulation services and agent
# ---------------------------------------------------------------------------


def wire_services(
    robots,
    robot_states,
    environment,
    artifacts_dir: Path,
    model: str,
    rules: str | None,
):
    assigner = JsonAssignmentService(artifacts_dir / "assignments.json")
    store = JsonSimulationStore(
        registry_path=artifacts_dir / "registry.json",
        state_path=artifacts_dir / "state.json",
        assignment_service=assigner,
    )

    for robot_id, robot in robots.items():
        store.add_robot(robot, robot_states[robot_id])

    runner = SimulationRunner(
        environment=environment,
        store=store,
        assignment_service=assigner,
    )

    agent = MODEL_REGISTRY[model](store, assigner, rules=rules)

    return runner, agent, store


# ---------------------------------------------------------------------------
# 5. Simulation loop
# ---------------------------------------------------------------------------


def run_loop(runner: SimulationRunner, agent: AssignmentAgent, store: BaseSimulationStore, tasks_to_spawn: list[SpawnTask]) -> None:
    def invoke(prompt: str) -> None:
        asyncio.run(agent.invoke(prompt, max_tool_calls=5))

    time_to_tasks: dict[Time, list[SpawnTask]] = {}

    for s in tasks_to_spawn:
        time_to_tasks.setdefault(s.time_to_spawn, []).append(s)


    for _ in range(MAX_TICKS):
        tasks_to_spawn_this_tick: list[SpawnTask] = time_to_tasks.get(runner._t_now, [])
        for spawn_task in tasks_to_spawn_this_tick:
            store.add_task(spawn_task.task_to_spawn, spawn_task.task_state)

        _, outcome = runner.step()

        should_reassign = outcome.tasks_spawned or outcome.tasks_completed or len(tasks_to_spawn_this_tick) > 0
        if should_reassign:
            invoke("Tasks changed. Reassign robots as needed.")


# ---------------------------------------------------------------------------
# 6. Write results
# ---------------------------------------------------------------------------


def write_results(runner, agent, results_path: Path, artifacts_dir: Path) -> None:
    sim = runner.stop()
    llm = agent.get_analysis()

    results = {
        "simulation": sim.to_json_dict(),
        "agent": llm.to_json_dict(),
    }

    results_path.write_text(json.dumps(results, indent=2))
    print(f"results written to {results_path}")

    replay = runner.get_replay()
    replay_path = artifacts_dir / "simulation_replay.json"
    replay_path.write_text(json.dumps(replay, indent=2))
    print(f"simulation replay written to {replay_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m experiments.run",
        usage="%(prog)s <scenario>/<override_variant> --model <model>",
    )
    parser.add_argument("condition", metavar="<scenario>/<override_variant>")
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    parts = args.condition.split("/")
    if len(parts) != 2:
        raise SystemExit(
            "condition must be in the form <scenario>/<override_variant>, e.g. scenario_01/baseline"
        )
    scenario, override_variant = parts

    validate_run(scenario, override_variant, args.model)
    model = args.model

    rules_path = EXPERIMENTS_DIR / scenario / override_variant / "rules.md"
    rules_text = rules_path.read_text() if rules_path.exists() else None
    rules = rules_text if rules_text and rules_text.strip() else None

    robots, robot_states, task_spawns, environment = load_definition(scenario)
    run_dir = make_run_dir(scenario, override_variant, model)
    runner, agent, store = wire_services(
        robots,
        robot_states,
        environment,
        run_dir / "artifacts",
        model,
        rules,
    )

    run_loop(runner, agent, store, task_spawns)
    write_results(runner, agent, run_dir / "results.json", run_dir / "artifacts")


if __name__ == "__main__":
    main()
