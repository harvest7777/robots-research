"""
Shared types and abstract interface for LLM providers.

Defines Message, Tool, and content types used across all providers,
plus the LLMProvider base class that each provider must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Shared content types
# ---------------------------------------------------------------------------


@dataclass
class TextContent:
    text: str


@dataclass
class ToolUseContent:
    id: str
    name: str
    args: dict


@dataclass
class ToolResultContent:
    tool_use_id: str
    content: str
    is_error: bool = False


Content = TextContent | ToolUseContent | ToolResultContent


# ---------------------------------------------------------------------------
# Message and Tool
# ---------------------------------------------------------------------------


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str | list[Content]


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict


# ---------------------------------------------------------------------------
# LLM response
# ---------------------------------------------------------------------------


@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[ToolUseContent] = field(default_factory=list)
    stop_reason: str = "end_turn"  # "end_turn" | "tool_use"


# ---------------------------------------------------------------------------
# Abstract provider
# ---------------------------------------------------------------------------


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str | None = None,
    ) -> LLMResponse: ...

    @property
    def supports_native_tools(self) -> bool:
        return True
