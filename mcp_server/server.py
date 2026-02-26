from mcp.server.fastmcp import FastMCP
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


if __name__ == "__main__":
    mcp.run()
