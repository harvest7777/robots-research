import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from pathfinding_algorithms import astar_pathfind
from scenario_loaders import load_simulation_from_dict
from simulation_models.assignment import Assignment

mcp = FastMCP("robots-sim")

_SCENARIO_PATH = Path(__file__).parent.parent / "scenarios" / "simple_test.json"


def _load_scenario_data() -> dict:
    with open(_SCENARIO_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def ping() -> str:
    """Health check. Returns 'pong'."""
    return "pong"


@mcp.tool()
def get_scenario() -> dict:
    """Get the current scenario: environment dimensions, robot starting positions
    and capabilities, and task locations and requirements. Call this before
    proposing assignments so you understand what robots and tasks exist."""
    return _load_scenario_data()


@mcp.tool()
def run_simulation(assignments: list[dict]) -> dict:
    """Run the simulation with a proposed set of robot-task assignments and return
    the outcome. Each assignment is {"task_id": <int>, "robot_ids": [<int>, ...]}.

    Returns whether all tasks completed, the makespan (ticks taken), and the
    final status of each task. Use this to evaluate your coordination plan.

    Example assignments: [{"task_id": 1, "robot_ids": [1]}]
    """
    data = _load_scenario_data()
    sim = load_simulation_from_dict(data, pathfinding_algorithm=astar_pathfind)

    sim.assignments = [
        Assignment(
            task_id=a["task_id"],
            robot_ids=frozenset(a["robot_ids"]),
        )
        for a in assignments
    ]

    result = sim.run(max_delta_time=200)

    per_task = [
        {
            "task_id": task.id,
            "status": sim.task_states[task.id].status.value,
            "work_done": sim.task_states[task.id].work_done.tick,
            "required_work_time": task.required_work_time.tick,
        }
        for task in sim.tasks
    ]

    return {
        "completed": result.completed,
        "tasks_succeeded": result.tasks_succeeded,
        "tasks_total": result.tasks_total,
        "makespan": result.makespan,
        "per_task": per_task,
    }


if __name__ == "__main__":
    mcp.run()
