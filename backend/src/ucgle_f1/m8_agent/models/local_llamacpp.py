"""llama.cpp (via llama-cpp-python) provider."""

from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncIterator

from .base import ChatEvent, Message, ProviderConfig


class LlamaCppProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    async def stream(
        self,
        messages: list[Message],
        tools: list[dict],
    ) -> AsyncIterator[ChatEvent]:
        try:
            from llama_cpp import Llama
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("install backend[llamacpp]") from exc

        model_path = Path.home() / ".ucgle_f1" / "models" / f"{self.config.model_id}.gguf"
        if not model_path.exists():
            raise RuntimeError(f"model not installed: {model_path}")
        llm = Llama(model_path=str(model_path), n_ctx=self.config.max_tokens * 2, seed=self.config.seed or 0)

        payload = [{"role": m.role, "content": m.content} for m in messages]
        out = llm.create_chat_completion(
            messages=payload,
            temperature=self.config.temperature,
            stream=True,
            max_tokens=self.config.max_tokens,
            tools=tools or None,
        )
        for chunk in out:  # type: ignore[assignment]
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
            if chunk["choices"][0].get("finish_reason"):
                yield ChatEvent(type="finish", finish_reason=chunk["choices"][0]["finish_reason"])
                return
