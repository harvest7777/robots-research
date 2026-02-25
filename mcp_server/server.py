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

