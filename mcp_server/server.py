from pathlib import Path

from mcp.server.fastmcp import FastMCP

from simulation.engine_rewrite.assignment import Assignment
from simulation.engine_rewrite.services.json_assignment_service import JsonAssignmentService
from simulation.domain.base_task import TaskId
from simulation.domain.robot_state import RobotId

mcp = FastMCP("robots-sim")

_ROOT = Path(__file__).parent.parent
_STATE_PATH = _ROOT / "sim_state_v2.json"
_ASSIGNMENTS_PATH = _ROOT / "sim_assignments_v2.json"

_assignment_service = JsonAssignmentService(_ASSIGNMENTS_PATH)


def _read_state() -> dict | None:
    if not _STATE_PATH.exists():
        return None
    import json
    with open(_STATE_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def ping() -> str:
    """Health check. Returns 'pong'."""
    return "pong"


@mcp.tool()
def get_current_tick() -> dict:
    """Get the current simulation tick.

    Returns an error if no simulation is running (start main_v2.py first).
    """
    state = _read_state()
    if state is None:
        return {"error": "No simulation state found. Start main_v2.py first."}
    return {"current_tick": state["current_tick"], "max_tick": state["max_tick"]}


@mcp.tool()
def get_simulation_state() -> dict:
    """Get the full live state of the running simulation.

    Returns the current tick and the live position/status of every robot
    and task, plus current assignments.

    WHEN TO CALL THIS:
    - Always call this FIRST before making any assignment decisions. You need
      to know which tasks exist, which robots are available, and their
      positions before choosing assignments.

    ASSIGNMENT WORKFLOW (follow in order):
      1. get_simulation_state()  — understand tasks, robots, and assignments
      2. assign_robots(...)      — write new assignments

    TO STOP ALL ROBOTS: call stop_all_robots() directly.

    Key facts about the data:
    - task_type values: "search", "move", "rescue_point", "work"
    - task status values: null (active), "done", "failed"
    - robot positions are (x, y) integer grid coordinates
    - "rescue_point" tasks appear in tasks list only after discovery
    - MoveTask "current_position" tracks where the object is right now
    - MoveTask "destination" is where it needs to go
    """
    state = _read_state()
    if state is None:
        return {"error": "No simulation state found. Start main_v2.py first."}
    return state


@mcp.tool()
def stop_all_robots() -> dict:
    """Stop all robots immediately by clearing all assignments.

    Robots with no assignment stay in place. Takes effect on the next
    simulation tick.
    """
    state = _read_state()
    if state is None:
        return {"error": "No simulation state found. Start main_v2.py first."}

    _assignment_service.clear()
    robot_ids = [r["robot_id"] for r in state["robots"]]
    return {"stopped_robot_ids": robot_ids}


@mcp.tool()
def assign_robots(assignments: list[dict]) -> dict:
    """Assign robots to tasks. Takes effect on the next simulation tick.

    REQUIRED PARAMETER:
      assignments: list of {"task_id": <int>, "robot_id": <int>}

    Rules:
    - Each entry assigns exactly one robot to one task.
    - To stop a specific robot, omit it from assignments (or call
      stop_all_robots() to clear everything).
    - Calling this again will upsert — existing assignments for robots not
      mentioned are unchanged.

    Example — assign robots 1, 2, and 3 all to task 3:
        assign_robots([
            {"task_id": 3, "robot_id": 1},
            {"task_id": 3, "robot_id": 2},
            {"task_id": 3, "robot_id": 3},
        ])

    Example — redirect robot 2 to task 1 while leaving others unchanged:
        assign_robots([{"task_id": 1, "robot_id": 2}])
    """
    new_assignments = [
        Assignment(
            task_id=TaskId(a["task_id"]),
            robot_id=RobotId(a["robot_id"]),
        )
        for a in assignments
    ]
    _assignment_service.update(new_assignments)
    return {"written": len(new_assignments)}


if __name__ == "__main__":
    mcp.run()
