"""Wire-format helpers for the visualisation streams (PROMPT 7 v2).

WS / SSE messages share a common envelope::

    {
      "type": "frame" | "header" | "end" | "error",
      "seq": <int>,
      "tau": <float>,
      "payload": <frame dict>
    }

The bytes-on-the-wire are ormsgpack when available (default);
JSON fallback ensures the server stays usable in environments
without the ormsgpack wheel.
"""

from __future__ import annotations

import json
from typing import Any, Literal


MessageType = Literal["header", "frame", "end", "error"]


def envelope(
    type_: MessageType,
    *,
    seq: int = 0,
    tau: float = 0.0,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical envelope dict."""
    return {
        "type": type_,
        "seq": seq,
        "tau": tau,
        "payload": payload or {},
    }


def encode(message: dict[str, Any]) -> bytes:
    """Encode a message dict; prefer ormsgpack, fall back to JSON UTF-8."""
    try:
        import ormsgpack  # type: ignore[import-not-found]
        return ormsgpack.packb(message)
    except ImportError:
        return json.dumps(message, separators=(",", ":")).encode("utf-8")


def decode(blob: bytes) -> dict[str, Any]:
    """Decode bytes into a dict; mirror of :func:`encode`."""
    try:
        import ormsgpack  # type: ignore[import-not-found]
        out = ormsgpack.unpackb(blob)
        return out if isinstance(out, dict) else {"payload": out}
    except ImportError:
        return json.loads(blob.decode("utf-8"))


def sse_format(message: dict[str, Any]) -> str:
    """Format a message for an EventSource (Server-Sent Events) channel.

    Each ``data:`` line is JSON; the ormsgpack path is reserved for
    binary WS frames. SSE clients always see JSON.
    """
    return f"data: {json.dumps(message, separators=(',', ':'))}\n\n"
