"""vLLM local-server provider (OpenAI-compatible backend)."""

from __future__ import annotations

import json
import os
from typing import AsyncIterator

from .base import ChatEvent, Message, ProviderConfig


class VLLMProvider:
    """Connects to a vLLM OpenAI-compatible server (default http://localhost:8000)."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.base_url = (config.extras or {}).get(
            "base_url", os.environ.get("VLLM_URL", "http://localhost:8000/v1"),
        )

    async def stream(
        self,
        messages: list[Message],
        tools: list[dict],
    ) -> AsyncIterator[ChatEvent]:
        import httpx

        payload = {
            "model": self.config.model_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self.config.temperature,
            "stream": True,
            "max_tokens": self.config.max_tokens,
            "seed": self.config.seed,
            "tools": tools or None,
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload,
            ) as resp:
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        yield ChatEvent(type="finish", finish_reason="stop")
                        return
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"]
                    if content := delta.get("content"):
                        yield ChatEvent(type="token", delta=content)
                    for tc in delta.get("tool_calls", []) or []:
                        args = tc["function"].get("arguments", "{}")
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {"_raw": args}
                        yield ChatEvent(type="tool_call", tool_call={
                            "id": tc.get("id"),
                            "name": tc["function"]["name"],
                            "arguments": args,
                        })
