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
import time

import litellm
from langsmith import traceable

from llm.agent_analysis import AgentAnalysis
from llm.agent_call_record import AgentCallRecord
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
        api_base: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._model = model
        self._system = system
        self._api_base = api_base
        self._api_key = api_key
        self._tools, self._handlers = make_tools(store, assignment_service)
        self._history: list[dict] = []
        self._records: list[AgentCallRecord] = []

    @traceable(run_type="chain", name="AssignmentAgent.invoke")
    async def invoke(self, message: str, max_tool_calls: int | None = None) -> tuple[str, int]:
        self._history.append({"role": "user", "content": message})

        tool_calls_made = 0
        tool_rounds = 0
        tokens_in = 0
        tokens_out = 0
        tool_call_counts: dict[str, int] = {}
        truncated_by_tool_limit = False
        started_at = time.time()
        final_content = ""

        while True:
            messages = self._history
            if self._system:
                messages = [{"role": "system", "content": self._system}] + self._history

            response = await litellm.acompletion(
                model=self._model,
                messages=messages,
                tools=self._tools,
                max_tokens=4096,
                api_base=self._api_base,
                api_key=self._api_key,
            )

            msg = response.choices[0].message
            if response.usage:
                tokens_in += response.usage.prompt_tokens or 0
                tokens_out += response.usage.completion_tokens or 0

            assistant_msg: dict = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                assistant_msg["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]
            self._history.append(assistant_msg)

            tool_limit_reached = max_tool_calls is not None and tool_calls_made >= max_tool_calls
            if not msg.tool_calls or tool_limit_reached:
                truncated_by_tool_limit = tool_limit_reached
                final_content = msg.content or ""
                break

            for tc in msg.tool_calls:
                tool_call_counts[tc.function.name] = tool_call_counts.get(tc.function.name, 0) + 1
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
            tool_rounds += 1

        self._records.append(AgentCallRecord(
            timestamp=started_at,
            latency_ms=int((time.time() - started_at) * 1000),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tool_rounds=tool_rounds,
            tool_call_counts=tool_call_counts,
            truncated_by_tool_limit=truncated_by_tool_limit,
        ))
        return final_content, tokens_in + tokens_out

    def get_analysis(self) -> AgentAnalysis:
        return AgentAnalysis.from_records(self._records)
