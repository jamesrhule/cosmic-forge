"""M8 — Agent orchestrator for UCGLE-F1.

Exposes the simulator as a typed MCP-style tool surface plus an SSE
``/v1/chat`` endpoint for non-MCP clients. Both front-ends call the
same tool functions — there is exactly one implementation per tool.

The server is started by ``ucgle-f1-agent`` (see pyproject scripts).
``build_app`` and ``run`` load the server on first use, so importing a
submodule (``auth`` in a worker's job process) doesn't load it.
"""

from __future__ import annotations

from typing import Any

__all__ = ["build_app", "run"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import server

        return getattr(server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
