"""Model selection + local model install/uninstall.

Provider factory routes ProviderConfig → a concrete ChatProvider.
Local models (GGUF / safetensors) live under
``~/.ucgle_f1/models/`` with a manifest.json next to each file.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import AsyncIterator

from ...domain import (
    InstallEvent,
    InstallProgress,
    InstallReady,
    InstallVerifying,
    ModelDescriptor,
    ModelStatus,
    ModelStatusNotInstalled,
    ModelStatusReady,
)
from .anthropic import AnthropicProvider
from .base import ChatProvider, ProviderConfig
from .local_llamacpp import LlamaCppProvider
from .local_ollama import OllamaProvider
from .local_vllm import VLLMProvider
from .openai import OpenAIProvider

_MODELS_DIR = Path.home() / ".ucgle_f1" / "models"


_PROVIDERS: dict[str, type[ChatProvider]] = {
    "openai": OpenAIProvider,     # type: ignore[dict-item]
    "anthropic": AnthropicProvider,  # type: ignore[dict-item]
    "ollama": OllamaProvider,     # type: ignore[dict-item]
    "llamacpp": LlamaCppProvider,  # type: ignore[dict-item]
    "vllm": VLLMProvider,         # type: ignore[dict-item]
}


def register_provider(name: str, cls: type[ChatProvider]) -> None:
    _PROVIDERS[name] = cls


def get_provider(config: ProviderConfig) -> ChatProvider:
    cls = _PROVIDERS.get(config.provider)
    if cls is None:
        raise ValueError(f"no provider: {config.provider}")
    return cls(config)  # type: ignore[call-arg]


# ── Local model management ─────────────────────────────────────────────


def _manifest_path(model_id: str) -> Path:
    return _MODELS_DIR / f"{model_id}.manifest.json"


def list_models() -> list[ModelDescriptor]:
    # Static recommended list + discovered local files.
    out: list[ModelDescriptor] = [
        ModelDescriptor(
            id="llama-3.1-8b-instruct-q4",
            displayName="Llama 3.1 8B Instruct (Q4_K_M)",
            provider="local", format="gguf",
            sizeBytes=4_780_000_000, contextWindow=131_072,
            license="Llama 3.1 Community License",
            source="https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct",
            recommended=True, tags=["gguf", "8b", "instruct"],
        ),
        ModelDescriptor(
            id="qwen2.5-14b-instruct-q4",
            displayName="Qwen 2.5 14B Instruct (Q4_K_M)",
            provider="local", format="gguf",
            sizeBytes=8_200_000_000, contextWindow=131_072,
            license="Apache-2.0",
            source="https://huggingface.co/Qwen/Qwen2.5-14B-Instruct",
            recommended=True, tags=["gguf", "14b", "instruct"],
        ),
        ModelDescriptor(
            id="gpt-4o-mini",
            displayName="GPT-4o mini (remote)",
            provider="remote", format="api",
            contextWindow=128_000, license="proprietary",
            source="https://platform.openai.com/docs/models",
            recommended=False, tags=["remote", "api"],
        ),
        ModelDescriptor(
            id="claude-sonnet-4-6",
            displayName="Claude Sonnet 4.6",
            provider="remote", format="api",
            contextWindow=200_000, license="proprietary",
            source="https://docs.anthropic.com",
            recommended=True, tags=["remote", "api"],
        ),
    ]
    return out


def model_status(model_id: str) -> ModelStatus:
    manifest = _manifest_path(model_id)
    if manifest.exists():
        m = json.loads(manifest.read_text())
        return ModelStatusReady(
            installedAt=datetime.fromisoformat(m["installedAt"]),
            diskBytes=int(m["diskBytes"]),
        )
    return ModelStatusNotInstalled()


async def install_model(model_id: str) -> AsyncIterator[InstallEvent]:
    """Stream install progress. Downloads are vendor-specific and
    intentionally stubbed here — the frontend/backend integration
    test drives this path with a fixture source.
    """
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)
    target = _MODELS_DIR / f"{model_id}.gguf"
    # Fake staged download — real implementations fetch from HF.
    total = 1_000
    for step in range(1, 11):
        yield InstallProgress(fraction=step / 10, downloadedBytes=step * 100, totalBytes=total)
    target.write_bytes(b"UCGLE-F1 placeholder model weights")
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    yield InstallVerifying()
    _manifest_path(model_id).write_text(json.dumps({
        "modelId": model_id,
        "installedAt": datetime.now(UTC).isoformat(),
        "diskBytes": target.stat().st_size,
        "checksum": checksum,
        "contextWindow": 131_072,
    }, indent=2))
    yield InstallReady()


def uninstall_model(model_id: str) -> None:
    manifest = _manifest_path(model_id)
    target = _MODELS_DIR / f"{model_id}.gguf"
    if target.exists():
        target.unlink()
    if manifest.exists():
        manifest.unlink()
    _ = shutil  # reserved for directory-backed models
