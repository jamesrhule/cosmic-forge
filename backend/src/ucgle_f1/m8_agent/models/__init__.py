"""ChatProvider implementations + local model registry."""

from __future__ import annotations

from .base import ChatEvent, ChatProvider, Message, ProviderConfig
from .registry import (
    get_provider,
    install_model,
    list_models,
    model_status,
    register_provider,
    uninstall_model,
)

__all__ = [
    "ChatEvent",
    "ChatProvider",
    "Message",
    "ProviderConfig",
    "get_provider",
    "install_model",
    "list_models",
    "model_status",
    "register_provider",
    "uninstall_model",
]
