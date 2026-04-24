"""Ollama local-model provider."""

from __future__ import annotations

import json
from typing import AsyncIterator

from .base import ChatEvent, Message, ProviderConfig


class OllamaProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    async def stream(
        self,
        messages: list[Message],
        tools: list[dict],
    ) -> AsyncIterator[ChatEvent]:
        try:
            import ollama  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("install backend[ollama] to use OllamaProvider") from exc

        response = await ollama.AsyncClient().chat(
            model=self.config.model_id,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            options={
                "temperature": self.config.temperature,
                "seed": self.config.seed,
            },
            stream=True,
            tools=tools or None,
        )
        async for part in response:  # type: ignore[union-attr]
            msg = part.get("message", {})
            if content := msg.get("content"):
                yield ChatEvent(type="token", delta=content)
            for tc in msg.get("tool_calls", []) or []:
                args = tc.get("function", {}).get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"_raw": args}
                yield ChatEvent(type="tool_call", tool_call={
                    "id": tc.get("id"),
                    "name": tc.get("function", {}).get("name"),
                    "arguments": args,
                })
            if part.get("done"):
                yield ChatEvent(type="finish", finish_reason="stop")
                return
