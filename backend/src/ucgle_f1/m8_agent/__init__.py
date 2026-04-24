"""M8 — Agent orchestrator for UCGLE-F1.

Exposes the simulator as a typed MCP-style tool surface plus an SSE
``/v1/chat`` endpoint for non-MCP clients. Both front-ends call the
same tool functions — there is exactly one implementation per tool.

The server is started by ``ucgle-f1-agent`` (see pyproject scripts).
"""

from __future__ import annotations

from .server import build_app, run

__all__ = ["build_app", "run"]
