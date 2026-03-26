"""
llm/agent.py

AssignmentAgent — drives an LLM through a tool-use loop to assign robots
to tasks via LiteLLM.

Usage
-----
    agent = AssignmentAgent(
        model="openai/gpt-4.1-mini",
        store=store,
        assignment_service=assigner,
        system="You are a robot task assignment system ...",
    )

    response = await agent.invoke("Tick 10: casualty Alpha was just discovered.")

`invoke` appends the message to the shared conversation history, runs the
tool loop to completion, and returns the final text reply.
"""

from __future__ import annotations

import json

import litellm
from langsmith import traceable

from llm.tools import make_tools
from simulation.engine_rewrite.services.base_assignment_service import BaseAssignmentService
from simulation.engine_rewrite.services.base_simulation_store import BaseSimulationStore


class AssignmentAgent:
    def __init__(
        self,
        model: str,
        store: BaseSimulationStore,
        assignment_service: BaseAssignmentService,
        system: str | None = None,
    ) -> None:
        self._model = model
        self._system = system
        self._tools, self._handlers = make_tools(store, assignment_service)
        self._history: list[dict] = []

    @traceable(run_type="chain", name="AssignmentAgent.invoke")
    async def invoke(self, message: str, max_tool_calls: int | None = None) -> tuple[str, int]:
        self._history.append({"role": "user", "content": message})

        tool_calls_made = 0
        total_tokens = 0

        while True:
            messages = self._history
            if self._system:
                messages = [{"role": "system", "content": self._system}] + self._history

            response = await litellm.acompletion(
                model=self._model,
                messages=messages,
                tools=self._tools,
                max_tokens=4096,
            )

            msg = response.choices[0].message
            total_tokens += response.usage.total_tokens if response.usage else 0

            assistant_msg: dict = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                assistant_msg["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]
            self._history.append(assistant_msg)

            if not msg.tool_calls:
                return msg.content or "", total_tokens

            if max_tool_calls is not None and tool_calls_made >= max_tool_calls:
                return msg.content or "", total_tokens

            for tc in msg.tool_calls:
                handler = self._handlers.get(tc.function.name)
                if handler is None:
                    result = f"Unknown tool: {tc.function.name}"
                else:
                    try:
                        result = handler(json.loads(tc.function.arguments))
                    except Exception as exc:
                        result = str(exc)

                self._history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            tool_calls_made += len(msg.tool_calls)
