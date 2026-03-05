"""
LLM provider implementation for OpenAI.

Translates the shared Message/Tool types to the OpenAI SDK format,
calls the API, and maps the response back to LLMResponse.
"""

import json

import openai

from llm.providers.base import (
    Content,
    LLMProvider,
    LLMResponse,
    Message,
    TextContent,
    Tool,
    ToolResultContent,
    ToolUseContent,
)
from dotenv import load_dotenv

load_dotenv()


def _to_openai_messages(
    messages: list[Message], system: str | None
) -> list[dict]:
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
            # Tool results become individual "tool" role messages.
            # Any plain text blocks become a single "user" message.
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


def _to_openai_tool(tool: Tool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o"):
        self._client = openai.AsyncOpenAI()
        self._model = model

    async def complete(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str | None = None,
    ) -> LLMResponse:
        openai_messages = _to_openai_messages(messages, system)
        openai_tools = [_to_openai_tool(t) for t in tools]

        kwargs: dict = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": openai_messages,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        msg = choice.message

        text = msg.content
        tool_calls = []

        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(ToolUseContent(
                    id=tc.id,
                    name=tc.function.name,
                    args=json.loads(tc.function.arguments),
                ))

        finish_reason = choice.finish_reason
        stop_reason = "tool_use" if finish_reason == "tool_calls" else "end_turn"

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
        )
