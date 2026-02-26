import anthropic

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


def _to_anthropic_content(content: str | list[Content]) -> str | list[dict]:
    if isinstance(content, str):
        return content

    blocks = []
    for item in content:
        if isinstance(item, TextContent):
            blocks.append({"type": "text", "text": item.text})
        elif isinstance(item, ToolUseContent):
            blocks.append({
                "type": "tool_use",
                "id": item.id,
                "name": item.name,
                "input": item.args,
            })
        elif isinstance(item, ToolResultContent):
            blocks.append({
                "type": "tool_result",
                "tool_use_id": item.tool_use_id,
                "content": item.content,
                "is_error": item.is_error,
            })
    return blocks


def _to_anthropic_tool(tool: Tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.AsyncAnthropic()
        self._model = model

    async def complete(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str | None = None,
    ) -> LLMResponse:
        anthropic_messages = [
            {"role": m.role, "content": _to_anthropic_content(m.content)}
            for m in messages
        ]
        anthropic_tools = [_to_anthropic_tool(t) for t in tools]

        kwargs: dict = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
        }
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = await self._client.messages.create(**kwargs)

        text = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolUseContent(
                    id=block.id,
                    name=block.name,
                    args=block.input,
                ))

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
        )
