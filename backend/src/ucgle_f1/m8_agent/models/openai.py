"""OpenAI ChatProvider — thin adapter.

Requires the optional ``openai`` extra. We keep the surface minimal
(one streaming method) so the same function drives the MCP tool
path and the /v1/chat SSE path.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

from .base import ChatEvent, Message, ProviderConfig


class OpenAIProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    async def stream(
        self,
        messages: list[Message],
        tools: list[dict],
    ) -> AsyncIterator[ChatEvent]:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("install backend[openai] to use OpenAIProvider") from exc

        client = AsyncOpenAI()
        payload_messages = [
            {"role": m.role, "content": m.content,
             **({"tool_call_id": m.tool_call_id} if m.tool_call_id else {}),
             **({"name": m.name} if m.name else {})}
            for m in messages
        ]
        stream = await client.chat.completions.create(
            model=self.config.model_id,
            messages=payload_messages,  # type: ignore[arg-type]
            tools=tools or None,  # type: ignore[arg-type]
            temperature=self.config.temperature,
            seed=self.config.seed,
            stream=True,
            max_tokens=self.config.max_tokens,
        )

        async for chunk in stream:
            ch = chunk.choices[0]
            delta = ch.delta
            if delta.content:
                yield ChatEvent(type="token", delta=delta.content)
            if getattr(delta, "tool_calls", None):
                for tc in delta.tool_calls:
                    args = tc.function.arguments or "{}"
                    try:
                        parsed = json.loads(args)
                    except json.JSONDecodeError:
                        parsed = {"_raw": args}
                    yield ChatEvent(type="tool_call", tool_call={
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": parsed,
                    })
            if ch.finish_reason is not None:
                yield ChatEvent(type="finish", finish_reason=ch.finish_reason)
