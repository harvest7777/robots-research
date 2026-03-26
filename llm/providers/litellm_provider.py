"""
LLM provider implementation backed by LiteLLM.

LiteLLM speaks the OpenAI wire format for all providers, so a single
conversion path covers OpenAI, Anthropic, Gemini, and any other
supported model.  Switch providers by changing the model string:

    LiteLLMProvider("openai/gpt-4.1-mini")
    LiteLLMProvider("anthropic/claude-sonnet-4-6")
    LiteLLMProvider("gemini/gemini-2.0-flash")
"""

from __future__ import annotations

import json

import litellm
from dotenv import load_dotenv
from langsmith import traceable

from llm.providers.base import (
    LLMProvider,
    LLMResponse,
    Message,
    TextContent,
    Tool,
    ToolResultContent,
    ToolUseContent,
)

load_dotenv()


def _to_litellm_messages(messages: list[Message], system: str | None) -> list[dict]:
    result = []

    if system:
        result.append({"role": "system", "content": system})

    for m in messages:
        if isinstance(m.content, str):
            result.append({"role": m.role, "content": m.content})
            continue

        if m.role == "assistant":
            text = None
            tool_calls = []
            for item in m.content:
                if isinstance(item, TextContent):
                    text = item.text
                elif isinstance(item, ToolUseContent):
                    tool_calls.append({
                        "id": item.id,
                        "type": "function",
                        "function": {
                            "name": item.name,
                            "arguments": json.dumps(item.args),
                        },
                    })
            msg: dict = {"role": "assistant", "content": text}
            if tool_calls:
                msg["tool_calls"] = tool_calls
            result.append(msg)

        elif m.role == "user":
            text_blocks = []
            for item in m.content:
                if isinstance(item, TextContent):
                    text_blocks.append(item.text)
                elif isinstance(item, ToolResultContent):
                    result.append({
                        "role": "tool",
                        "tool_call_id": item.tool_use_id,
                        "content": item.content,
                    })
            if text_blocks:
                result.append({"role": "user", "content": "\n".join(text_blocks)})

    return result


def _to_litellm_tool(tool: Tool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


class LiteLLMProvider(LLMProvider):
    def __init__(self, model: str):
        self._model = model

    @traceable(run_type="llm", name="LiteLLM.complete")
    async def complete(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str | None = None,
    ) -> LLMResponse:
        kwargs: dict = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": _to_litellm_messages(messages, system),
        }
        litellm_tools = [_to_litellm_tool(t) for t in tools]
        if litellm_tools:
            kwargs["tools"] = litellm_tools

        response = await litellm.acompletion(**kwargs)

        msg = response.choices[0].message
        text = msg.content
        tool_calls = []

        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(ToolUseContent(
                    id=tc.id,
                    name=tc.function.name,
                    args=json.loads(tc.function.arguments),
                ))

        tokens_used = 0
        if response.usage:
            tokens_used = response.usage.total_tokens or 0

        return LLMResponse(text=text, tool_calls=tool_calls, tokens_used=tokens_used)
