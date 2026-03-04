from pathlib import Path

from mcp.server.fastmcp import FastMCP

from services import JsonAssignmentService, JsonSimulationStateService
from simulation_models.assignment import Assignment, RobotId
from simulation_models.task import TaskId
from simulation_models.time import Time

mcp = FastMCP("robots-sim")

_ROOT = Path(__file__).parent.parent
_STATE_PATH = _ROOT / "sim_state.json"
_ASSIGNMENTS_PATH = _ROOT / "sim_assignments.json"

_state_service = JsonSimulationStateService(_STATE_PATH)
_assignment_service = JsonAssignmentService(_ASSIGNMENTS_PATH)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def ping() -> str:
    """Health check. Returns 'pong'."""
    return "pong"


@mcp.tool()
def get_simulation_state() -> dict:
    """Get the current live state of the running simulation.

    Returns the current tick, scenario ID, and the live position/status of
    every robot and task. Call this before writing assignments so you have
    accurate, up-to-date context.

    Returns None if no simulation has been started yet.
    """
    state = _state_service.read()
    if state is None:
        return {"error": "No simulation state found. Start main.py first."}
    return {
        "scenario_id": state.scenario_id,
        "tick": state.tick,
        "robots": [
            {
                "robot_id": r.robot_id,
                "x": r.x,
                "y": r.y,
                "battery_level": r.battery_level,
            }
            for r in state.robots
        ],
        "tasks": [
            {
                "task_id": t.task_id,
                "status": t.status.value,
                "work_done_ticks": t.work_done_ticks,
                "assigned_robot_ids": t.assigned_robot_ids,
            }
            for t in state.tasks
        ],
    }


@mcp.tool()
def assign_robots(assignments: list[dict], assign_at_tick: int) -> dict:
    """Override robot-task assignments starting at a given simulation tick.

    Each assignment is {"task_id": <int>, "robot_ids": [<int>, ...]}.
    assign_at_tick must be >= the current tick (use get_simulation_state to
    check). Assignments with a higher assign_at always win, so this safely
    stacks on top of any existing assignments.

    Example:
        assign_robots([{"task_id": 2, "robot_ids": [1, 3]}], assign_at_tick=10)
    """
    new_assignments = [
        Assignment(
            task_id=TaskId(a["task_id"]),
            robot_ids=frozenset(RobotId(rid) for rid in a["robot_ids"]),
            assign_at=Time(assign_at_tick),
        )
        for a in assignments
    ]
    _assignment_service.add_assignments(new_assignments)
    return {
        "written": len(new_assignments),
        "assign_at_tick": assign_at_tick,
    }


if __name__ == "__main__":
    mcp.run()
