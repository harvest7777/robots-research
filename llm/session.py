"""
Conversation session: orchestrates the LLM ↔ MCP tool-use loop.

Maintains message history, fetches available tools from the MCP server,
and drives the cycle of LLM completions → tool calls → tool results
until the model returns a final answer.
"""

import logging

from llm.mcp_client import MCPClient
from llm.providers.base import (
    LLMProvider,
    Message,
    TextContent,
    ToolResultContent,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a robot fleet coordinator connected to a live simulation via MCP tools.

AVAILABLE TOOLS:
- get_simulation_state()   — returns all robots, tasks, and the current tick
- get_current_tick()       — returns current_tick and max_tick
- assign_robots(assignments, assign_at_tick) — schedules robot-task assignments
- stop_all_robots()        — immediately stops every robot (assigns all to IDLE)
- ping()                   — health check

RULES — follow these exactly:

When the user asks to ASSIGN robots to tasks:
  1. Call get_simulation_state() to see all robots and tasks.
  2. Call get_current_tick() to get the current tick.
  3. Call assign_robots(assignments=[...], assign_at_tick=current_tick+1)
     where assignments is a list of {"task_id": <int>, "robot_ids": [<int>, ...]}.

When the user asks to STOP all robots:
  - Call stop_all_robots() directly. Do not call assign_robots for this.

When the user asks about simulation STATE (robots, tasks, progress):
  - Call get_simulation_state() and summarise the result.

task_id 0 is always the IDLE task. Assigning a robot to task_id 0 stops it.
assign_at_tick must always be >= current_tick. Use current_tick + 1 for ASAP.\
"""


class Session:
    def __init__(
        self,
        provider: LLMProvider,
        mcp: MCPClient,
        system: str = SYSTEM_PROMPT,
    ):
        self._provider = provider
        self._mcp = mcp
        self._system = system
        self._history: list[Message] = []

    async def send(self, user_message: str) -> str:
        self._history.append(Message(role="user", content=user_message))
        tools = await self._mcp.list_tools()

        while True:
            response = await self._provider.complete(
                self._history, tools, system=self._system
            )

            if not response.tool_calls:
                # Final answer — record and return
                self._history.append(
                    Message(role="assistant", content=response.text or "")
                )
                return response.text or ""

            # Record assistant message (text + tool calls)
            assistant_content = []
            if response.text:
                assistant_content.append(TextContent(text=response.text))
            assistant_content.extend(response.tool_calls)
            self._history.append(Message(role="assistant", content=assistant_content))

            # Execute each tool call and collect results
            tool_results = []
            for tool_call in response.tool_calls:
                logger.info("→ %s(%s)", tool_call.name, tool_call.args)
                result = await self._mcp.call_tool(tool_call.name, tool_call.args)
                logger.info("← %s", result[:120])
                tool_results.append(
                    ToolResultContent(tool_use_id=tool_call.id, content=result)
                )

            self._history.append(Message(role="user", content=tool_results))
