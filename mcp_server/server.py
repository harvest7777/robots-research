from pathlib import Path

from mcp.server.fastmcp import FastMCP

from services import JsonAssignmentService, JsonSimulationStateService
from simulation_models.assignment import Assignment
from simulation_models.robot_state import RobotId
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
    return {"current_tick": state.current_tick, "max_tick": state.max_tick}


@mcp.tool()
def get_simulation_state() -> dict:
    """Get the full live state of the running simulation.

    Returns the current tick, max tick, and the live position/status of every
    robot and task.

    WHEN TO CALL THIS:
    - Always call this FIRST before making any assignment decisions. You need
      to know which tasks exist, which robots are available, and what is
      already in progress before choosing assignments.

    ASSIGNMENT WORKFLOW (follow in order):
      1. get_simulation_state()  — understand tasks and robots
      2. get_current_tick()      — get the tick to schedule at
      3. assign_robots(...)      — write the assignments

    TO STOP ALL ROBOTS: call stop_all_robots() directly — do not use this
    tool for that purpose.

    Key facts about the data:
    - task_id 0 is always the IDLE task — assign robots here to stop them.
    - task status values: unassigned, assigned, in_progress, done, failed.
    - robot positions are (x, y) floats in grid units.
    """
    state = _state_service.read()
    if state is None:
        return {"error": "No simulation state found. Start main.py first."}
    return {
        "scenario_id": state.scenario_id,
        "current_tick": state.current_tick,
        "max_tick": state.max_tick,
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

    assign_at = state.current_tick + 1
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

    REQUIRED PARAMETERS — both must be provided:
      assignments    : list of {"task_id": <int>, "robot_ids": [<int>, ...]}
      assign_at_tick : int — the tick at which these assignments take effect

    Rules:
    - task_id 0 is the IDLE task — assign robots here to stop them.
    - assign_at_tick must be >= current_tick (call get_current_tick first).
    - For urgent / ASAP actions: use current_tick + 1 as assign_at_tick.
    - Higher assign_at always wins, so new calls safely stack on existing ones.

    Example — stop robot 2 immediately (current_tick = 7):
        assign_robots(
            assignments=[{"task_id": 0, "robot_ids": [2]}],
            assign_at_tick=8
        )

    Example — redirect robots 1 and 3 to task 5 at tick 20:
        assign_robots(
            assignments=[{"task_id": 5, "robot_ids": [1, 3]}],
            assign_at_tick=20
        )
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
