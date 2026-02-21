import json

from mcp.server.fastmcp import FastMCP

from mcp_server.sim_state import fork_sim, get_live_sim
from simulation_models.assignment import Assignment, RobotId
from simulation_models.position import Position
from simulation_models.task import TaskId

mcp = FastMCP("robots-sim")


# ---------------------------------------------------------------------------
# Existing tools
# ---------------------------------------------------------------------------


@mcp.tool()
def ping() -> str:
    """Health check. Returns 'pong'."""
    return "pong"


@mcp.tool()
def hello(name: str) -> str:
    """Return a greeting for the given name."""
    return f"Hello, {name}!"


# ---------------------------------------------------------------------------
# Simulation tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_state() -> str:
    """
    Return the current simulation state as a JSON object.

    Includes the current tick, all robots (id, position, battery, capabilities,
    speed), and all tasks (id, type, status, target location, work progress,
    required capabilities).

    This is the primary way for the LLM to observe the warehouse before making
    an assignment decision.
    """
    sim = get_live_sim()
    snap = sim.snapshot()

    robots_out = []
    for robot in snap.robots:
        state = snap.robot_states[robot.id]
        robots_out.append(
            {
                "id": int(robot.id),
                "capabilities": [c.value for c in robot.capabilities],
                "speed": robot.speed,
                "x": round(state.position.x, 3),
                "y": round(state.position.y, 3),
                "battery": round(state.battery_level, 4),
            }
        )

    tasks_out = []
    for task in snap.tasks:
        state = snap.task_states[task.id]
        target = None
        if task.spatial_constraint is not None:
            sc = task.spatial_constraint
            if isinstance(sc.target, Position):
                target = {"x": sc.target.x, "y": sc.target.y}
            else:
                target = {"zone_id": int(sc.target)}
        tasks_out.append(
            {
                "id": int(task.id),
                "type": task.type.value,
                "priority": task.priority,
                "status": state.status.value,
                "required_capabilities": [c.value for c in task.required_capabilities],
                "work_done": state.work_done.tick,
                "required_work_time": task.required_work_time.tick,
                "target": target,
                "assigned_robot_ids": [int(r) for r in state.assigned_robot_ids],
            }
        )

    return json.dumps(
        {
            "t": snap.t_now.tick if snap.t_now else 0,
            "environment": {"width": snap.env.width, "height": snap.env.height},
            "robots": robots_out,
            "tasks": tasks_out,
        }
    )


def _parse_assignments(assignments: str) -> list[Assignment]:
    """Parse a JSON string of assignments into Assignment objects."""
    raw = json.loads(assignments)
    return [
        Assignment(
            task_id=TaskId(a["task_id"]),
            robot_ids=frozenset(RobotId(r) for r in a["robot_ids"]),
        )
        for a in raw
    ]


@mcp.tool()
def evaluate_assignment(assignments: str, ticks: int = 50) -> str:
    """
    Hypothetically run the simulation with the given assignments and return metrics.

    Forks the current live simulation state, applies the provided assignments as
    a fixed strategy, steps the fork for `ticks` ticks, then returns outcome
    metrics. The live simulation is NOT affected.

    Use this to compare different assignment strategies before committing to one
    with override_assignment().

    assignments: JSON array of {"task_id": int, "robot_ids": [int, ...]} objects
                 e.g. '[{"task_id": 1, "robot_ids": [2, 3]}]'
    ticks:       Number of simulation ticks to evaluate over (default 50)
    """
    parsed = _parse_assignments(assignments)

    live = get_live_sim()
    initial_battery = {robot.id: live.robot_states[robot.id].battery_level for robot in live.robots}

    fork = fork_sim(parsed)
    initial_tick = fork.t_now.tick

    for _ in range(ticks):
        fork.step()

    snap = fork.snapshot()

    task_outcomes = []
    for task in snap.tasks:
        state = snap.task_states[task.id]
        task_outcomes.append(
            {
                "task_id": int(task.id),
                "status": state.status.value,
                "work_done": state.work_done.tick,
                "required_work_time": task.required_work_time.tick,
                "completed_at_tick": state.completed_at.tick if state.completed_at else None,
            }
        )

    robot_outcomes = []
    for robot in snap.robots:
        state = snap.robot_states[robot.id]
        battery_used = round(initial_battery[robot.id] - state.battery_level, 4)
        robot_outcomes.append(
            {
                "robot_id": int(robot.id),
                "battery_remaining": round(state.battery_level, 4),
                "battery_used": battery_used,
                "final_x": round(state.position.x, 3),
                "final_y": round(state.position.y, 3),
            }
        )

    all_done = all(o["status"] == "done" for o in task_outcomes)

    return json.dumps(
        {
            "ticks_elapsed": snap.t_now.tick - initial_tick,
            "all_tasks_completed": all_done,
            "task_outcomes": task_outcomes,
            "robot_outcomes": robot_outcomes,
        }
    )


@mcp.tool()
def override_assignment(assignments: str) -> str:
    """
    Override the live simulation's assignment strategy with the given assignments.

    On every subsequent tick, the live simulation will use these assignments:
    robots will navigate to their assigned task targets and perform work.

    Call step_simulation() after this to advance the live sim.

    assignments: JSON array of {"task_id": int, "robot_ids": [int, ...]} objects
                 e.g. '[{"task_id": 1, "robot_ids": [2, 3]}]'
    """
    parsed = _parse_assignments(assignments)
    live = get_live_sim()
    live.assignment_algorithm = lambda tasks, robots: parsed
    summary = ", ".join(
        f"task {int(a.task_id)} -> robots {sorted(int(r) for r in a.robot_ids)}"
        for a in parsed
    )
    return f"Assignment overridden ({len(parsed)} assignment(s)): {summary}"


@mcp.tool()
def step_simulation(ticks: int = 1) -> str:
    """
    Advance the live simulation by the given number of ticks.

    Use this after override_assignment() to let the sim run with the new
    strategy. Returns a brief state summary after stepping.

    ticks: Number of ticks to advance (default 1)
    """
    live = get_live_sim()
    for _ in range(ticks):
        live.step()

    snap = live.snapshot()
    task_summary = ", ".join(
        f"task {int(t.id)}={snap.task_states[t.id].status.value}" for t in snap.tasks
    )
    return f"Stepped {ticks} tick(s). t={snap.t_now.tick}. Tasks: {task_summary}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
