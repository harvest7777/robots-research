"""
Thin wrapper around an MCP ClientSession.

Exposes list_tools() and call_tool() in terms of the shared Tool type
so the session layer never imports directly from the mcp package.
"""

from mcp import ClientSession

from llm.providers.base import Tool


class MCPClient:
    def __init__(self, session: ClientSession):
        self._session = session

    async def list_tools(self) -> list[Tool]:
        result = await self._session.list_tools()
        return [
            Tool(
                name=t.name,
                description=t.description or "",
                input_schema=t.inputSchema if isinstance(t.inputSchema, dict)
                    else {"type": "object", "properties": {}},
            )
            for t in result.tools
        ]

    async def call_tool(self, name: str, args: dict) -> str:
        result = await self._session.call_tool(name, args)
        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts) if parts else "OK"
