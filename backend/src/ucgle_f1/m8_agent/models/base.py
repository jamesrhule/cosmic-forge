"""ChatProvider protocol — shared by every vendor adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Literal, Protocol


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_call_id: str | None = None


@dataclass
class ProviderConfig:
    model_id: str
    provider: Literal["openai", "anthropic", "ollama", "llamacpp", "vllm"]
    temperature: float = 0.0
    seed: int | None = 0
    max_tokens: int = 4096
    extras: dict[str, Any] | None = None


@dataclass
class ChatEvent:
    type: Literal["token", "tool_call", "finish", "error"]
    delta: str | None = None
    tool_call: dict | None = None
    finish_reason: str | None = None
    error: str | None = None


class ChatProvider(Protocol):
    """A streaming chat provider.

    Implementations MUST:
    - stream partial tokens as ``ChatEvent(type='token')``
    - emit ``ChatEvent(type='tool_call')`` when the model calls a tool
    - close with ``ChatEvent(type='finish')`` or ``type='error'``
    - honour ``config.temperature`` and ``config.seed`` for determinism
    """

    config: ProviderConfig

    def stream(
        self,
        messages: list[Message],
        tools: list[dict],
    ) -> AsyncIterator[ChatEvent]: ...
