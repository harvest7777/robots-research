from google import genai
from google.genai import types

from dotenv import load_dotenv

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

load_dotenv()


def _to_gemini_contents(messages: list[Message]) -> list[types.Content]:
    result = []

    for m in messages:
        role = "model" if m.role == "assistant" else "user"

        if isinstance(m.content, str):
            result.append(types.Content(role=role, parts=[types.Part(text=m.content)]))
            continue

        parts = []
        function_responses = []

        for item in m.content:
            if isinstance(item, TextContent):
                parts.append(types.Part(text=item.text))
            elif isinstance(item, ToolUseContent):
                parts.append(types.Part(
                    function_call=types.FunctionCall(name=item.name, args=item.args)
                ))
            elif isinstance(item, ToolResultContent):
                # Gemini expects function responses as their own user turn.
                function_responses.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=item.tool_use_id,
                        response={"result": item.content, "is_error": item.is_error},
                    )
                ))

        if parts:
            result.append(types.Content(role=role, parts=parts))
        if function_responses:
            result.append(types.Content(role="user", parts=function_responses))

    return result


def _to_gemini_tool(tools: list[Tool]) -> types.Tool | None:
    if not tools:
        return None
    return types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name=t.name,
            description=t.description,
            parameters=t.input_schema,
        )
        for t in tools
    ])


class GeminiProvider(LLMProvider):
    def __init__(self, model: str = "gemini-2.0-flash"):
        self._client = genai.Client()
        self._model = model

    async def complete(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str | None = None,
    ) -> LLMResponse:
        contents = _to_gemini_contents(messages)
        gemini_tool = _to_gemini_tool(tools)

        config = types.GenerateContentConfig(
            max_output_tokens=4096,
            system_instruction=system,
            tools=[gemini_tool] if gemini_tool else None,
        )

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        text = None
        tool_calls = []

        for part in candidate.content.parts:
            if part.text:
                text = part.text
            elif part.function_call:
                tool_calls.append(ToolUseContent(
                    id=part.function_call.name,
                    name=part.function_call.name,
                    args=dict(part.function_call.args),
                ))

        stop_reason = "tool_use" if tool_calls else "end_turn"

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
        )
