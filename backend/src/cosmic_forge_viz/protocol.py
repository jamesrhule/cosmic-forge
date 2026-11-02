"""Wire format for the visualization streams.

Every WebSocket message is one binary envelope::

    {"type": "header" | "frame" | "end" | "error",
     "seq": <int>, "tau": <float>, "payload": <dict>}

encoded with ormsgpack when installed (JSON UTF-8 otherwise). For
``type == "frame"`` the payload is the frame dict
(``BaseFrame.model_dump(mode="json")``). SSE uses the same messages
with the type as the ``event:`` name — see :func:`sse_event`.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from .schema import BaseFrame, frame_for_domain

MessageType = Literal["header", "frame", "end", "error"]


def _ormsgpack() -> Any | None:
    try:
        import ormsgpack  # type: ignore[import-not-found]
    except ImportError:
        return None
    return ormsgpack


def has_msgpack() -> bool:
    return _ormsgpack() is not None


def envelope(
    type_: MessageType,
    *,
    seq: int = 0,
    tau: float = 0.0,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {"type": type_, "seq": seq, "tau": tau, "payload": payload or {}}


def encode(message: dict[str, Any]) -> bytes:
    """Encode a message dict: msgpack when available, else compact JSON."""
    om = _ormsgpack()
    if om is not None:
        return om.packb(message, option=om.OPT_SERIALIZE_NUMPY)
    return json.dumps(message, separators=(",", ":")).encode("utf-8")


def decode(blob: bytes) -> dict[str, Any]:
    """Inverse of :func:`encode` (accepts JSON bytes even when msgpack is present)."""
    om = _ormsgpack()
    if om is not None:
        try:
            out = om.unpackb(blob)
        except Exception:
            out = json.loads(blob.decode("utf-8"))
    else:
        out = json.loads(blob.decode("utf-8"))
    return out if isinstance(out, dict) else {"payload": out}


def encode_frame(frame: BaseFrame, *, seq: int = 0) -> bytes:
    """Encode ``frame`` as a ``type="frame"`` envelope."""
    return encode(
        envelope("frame", seq=seq, tau=float(frame.tau), payload=frame.model_dump(mode="json"))
    )


def decode_frame(data: bytes) -> BaseFrame:
    """Parse bytes into a domain-typed frame (frame envelope or bare frame dict)."""
    message = decode(data)
    payload = message.get("payload") if message.get("type") == "frame" else message
    if not isinstance(payload, dict) or "domain" not in payload:
        raise ValueError("decoded message is not a frame (missing `domain`)")
    return frame_for_domain(str(payload["domain"])).model_validate(payload)


def sse_event(event: str, data: dict[str, Any]) -> str:
    """One named Server-Sent Event; data is compact JSON on one line."""
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def sse_format(message: dict[str, Any]) -> str:
    """An unnamed SSE event carrying a whole envelope (``data:`` only)."""
    return f"data: {json.dumps(message, separators=(',', ':'))}\n\n"


__all__ = [
    "MessageType",
    "decode",
    "decode_frame",
    "encode",
    "encode_frame",
    "envelope",
    "has_msgpack",
    "sse_event",
    "sse_format",
]
