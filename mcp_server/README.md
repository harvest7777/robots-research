# Robots MCP Server

A small [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server named **robots-sim**, built with [FastMCP](https://github.com/jlowin/fastmcp). It exposes simple tools for health checks and greetings.

## What it does

The server provides two tools:

| Tool    | Description                            | Parameters   |
| ------- | -------------------------------------- | ------------ |
| `ping`  | Health check. Returns `"pong"`.        | (none)       |
| `hello` | Returns a greeting for the given name. | `name` (str) |

## Hello World

The minimal MCP server — one tool, a few lines:

```python
from fastmcp import FastMCP

mcp = FastMCP("hello-world")

@mcp.tool()
def hello(name: str = "World") -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

Run it:

```bash
python server.py
```

That's it. The `@mcp.tool()` decorator registers the function as a callable tool. The docstring becomes the tool description Claude sees. `mcp.run()` starts the server over stdio.

---

## How to run it

### Prerequisites

From the project root, install dependencies:

```bash
pip install -r requirements.txt
```

### Run the server (stdio)

From the project root:

```bash
python -m mcp_server.server
```

The server uses **stdio** transport: it reads JSON-RPC from stdin and writes responses to stdout. MCP clients (e.g. Cursor, Claude Desktop) typically run this command and communicate over stdio.

### Use with Cursor

Add the server to your Cursor MCP config (e.g. in Cursor Settings → MCP) so Cursor can call the tools:

```json
{
  "mcpServers": {
    "robots-sim": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/robots"
    }
  }
}
```

Replace `/path/to/robots` with the absolute path to this project.

## Tests

From the project root:

```bash
pytest mcp_server/
```

Tests use the FastMCP in-process client to call `ping` and `hello` and to verify the tools are listed.
