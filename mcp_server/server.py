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

_IDLE_TASK_ID = TaskId(0)

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
def get_current_tick() -> dict:
    """Get the current simulation tick.

    Use this whenever you need to act urgently — read the tick, then pass
    tick + 1 as assign_at_tick to assign_robots so the change takes effect
    on the very next simulation step.

    Returns an error if no simulation is running.
    """
    state = _state_service.read()
    if state is None:
        return {"error": "No simulation state found. Start main.py first."}
    return {"tick": state.tick}


@mcp.tool()
def get_simulation_state() -> dict:
    """Get the full live state of the running simulation.

    Returns the current tick, and the live position/status of every robot and
    task. Use this to understand the scenario before making assignment decisions.

    Key facts about the data:
    - task_id 0 is always the IDLE task — assign robots here to stop them.
    - task status values: unassigned, assigned, in_progress, done, failed.
    - robot positions are (x, y) floats in grid units.

    For urgent actions (e.g. "stop all robots now"), call get_current_tick
    first, then act immediately using tick + 1 as assign_at_tick.
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
def stop_all_robots() -> dict:
    """Stop all robots immediately by assigning them to the IDLE task (task_id 0).

    Use this for any urgent halt: "stop", "freeze", "pause all robots", etc.
    Reads the current tick and schedules the IDLE assignment for tick + 1 so
    it takes effect on the very next simulation step.

    Returns the tick at which robots will stop.
    """
    state = _state_service.read()
    if state is None:
        return {"error": "No simulation state found. Start main.py first."}

    assign_at = state.tick + 1
    all_robot_ids = frozenset(RobotId(r.robot_id) for r in state.robots)
    _assignment_service.add_assignments([
        Assignment(
            task_id=_IDLE_TASK_ID,
            robot_ids=all_robot_ids,
            assign_at=Time(assign_at),
        )
    ])
    return {
        "stopped_robot_ids": list(all_robot_ids),
        "effective_at_tick": assign_at,
    }


@mcp.tool()
def assign_robots(assignments: list[dict], assign_at_tick: int) -> dict:
    """Override robot-task assignments starting at a given simulation tick.

    Each assignment is {"task_id": <int>, "robot_ids": [<int>, ...]}.

    Key rules:
    - task_id 0 is the IDLE task — assign robots here to stop them.
    - assign_at_tick must be >= the current tick (call get_current_tick first).
    - For urgent / ASAP actions: use current_tick + 1 as assign_at_tick.
    - Assignments with a higher assign_at always win, so this safely stacks
      on top of any existing assignments without corrupting history.

    Example — stop robot 2 immediately:
        get_current_tick() -> {"tick": 7}
        assign_robots([{"task_id": 0, "robot_ids": [2]}], assign_at_tick=8)

    Example — redirect robot 1 to task 3 at tick 20:
        assign_robots([{"task_id": 3, "robot_ids": [1]}], assign_at_tick=20)
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
