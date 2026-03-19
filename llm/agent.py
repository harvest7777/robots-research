"""
llm/agent.py

AssignmentAgent — drives an LLM through a tool-use loop to assign robots
to tasks.

Usage
-----
    agent = AssignmentAgent(
        provider=AnthropicProvider(),
        store=store,
        assignment_service=assigner,
        system="You are a robot task assignment system ...",
    )

    response = await agent.invoke("Tick 10: casualty Alpha was just discovered.")

`invoke` appends the message to the shared conversation history, runs the
provider's tool loop to completion, and returns the final text reply.
The caller decides when to call invoke — the agent never writes assignments
on its own.
"""

from __future__ import annotations

from llm.providers.base import (
    LLMProvider,
    Message,
    TextContent,
    ToolResultContent,
    ToolUseContent,
)
from llm.tools import make_tools
from simulation.engine_rewrite.services.base_assignment_service import BaseAssignmentService
from simulation.engine_rewrite.services.base_simulation_store import BaseSimulationStore


class AssignmentAgent:
    def __init__(
        self,
        provider: LLMProvider,
        store: BaseSimulationStore,
        assignment_service: BaseAssignmentService,
        system: str | None = None,
    ) -> None:
        self._provider = provider
        self._system = system
        self._tools, self._handlers = make_tools(store, assignment_service)
        self._history: list[Message] = []

    async def invoke(self, message: str) -> str:
        self._history.append(Message(role="user", content=message))

        while True:
            response = await self._provider.complete(
                messages=self._history,
                tools=self._tools,
                system=self._system,
            )

            # Build the assistant turn content so the history stays consistent
            # across providers (always a list so tool use blocks can be appended).
            assistant_content: list = []
            if response.text:
                assistant_content.append(TextContent(text=response.text))
            assistant_content.extend(response.tool_calls)

            self._history.append(Message(role="assistant", content=assistant_content))

            if not response.tool_calls:
                return response.text or ""

            # Dispatch all tool calls and collect results into one user turn.
            tool_results: list[ToolResultContent] = []
            for call in response.tool_calls:
                handler = self._handlers.get(call.name)
                if handler is None:
                    result = ToolResultContent(
                        tool_use_id=call.id,
                        content=f"Unknown tool: {call.name}",
                    )
                else:
                    try:
                        content = handler(call.args)
                        result = ToolResultContent(tool_use_id=call.id, content=content)
                    except Exception as exc:
                        result = ToolResultContent(
                            tool_use_id=call.id,
                            content=str(exc),
                        )
                tool_results.append(result)

            self._history.append(Message(role="user", content=tool_results))
