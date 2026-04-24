"""Anthropic ChatProvider — streams Messages API events.

Requires the ``anthropic`` extra (``pip install backend[anthropic]``).
"""

from __future__ import annotations

from typing import AsyncIterator

from .base import ChatEvent, Message, ProviderConfig


class AnthropicProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    async def stream(
        self,
        messages: list[Message],
        tools: list[dict],
    ) -> AsyncIterator[ChatEvent]:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("install backend[anthropic] to use AnthropicProvider") from exc

        client = anthropic.AsyncAnthropic()
        system_parts = [m.content for m in messages if m.role == "system"]
        convo = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in {"user", "assistant"}
        ]

        async with client.messages.stream(
            model=self.config.model_id,
            max_tokens=self.config.max_tokens,
            system="\n".join(system_parts) or None,
            temperature=self.config.temperature,
            tools=tools or None,  # type: ignore[arg-type]
            messages=convo,  # type: ignore[arg-type]
        ) as stream:
            async for ev in stream:
                t = getattr(ev, "type", "")
                if t == "content_block_delta" and hasattr(ev, "delta"):
                    d = ev.delta
                    if getattr(d, "type", "") == "text_delta":
                        yield ChatEvent(type="token", delta=d.text)
                elif t == "content_block_start":
                    blk = getattr(ev, "content_block", None)
                    if getattr(blk, "type", "") == "tool_use":
                        yield ChatEvent(type="tool_call", tool_call={
                            "id": blk.id,
                            "name": blk.name,
                            "arguments": blk.input,
                        })
                elif t == "message_stop":
                    yield ChatEvent(type="finish", finish_reason="stop")
