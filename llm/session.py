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
You are a robot fleet coordinator. For every user message, always:
1. Call get_scenario to understand the robots and tasks.
2. Try every viable robot-task assignment combination using run_simulation.
3. Pick the assignment with the lowest makespan that completed all tasks.
4. Reply with only: the winning assignment (robot → task) and its makespan.
No extra commentary. No explanations. Just the result.\
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
