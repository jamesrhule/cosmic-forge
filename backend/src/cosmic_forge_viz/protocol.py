"""msgpack framing for the WS endpoint.

`encode_frame` serializes a Pydantic frame to bytes; `decode_frame`
parses bytes back into a domain-typed frame. msgpack is preferred for
its 30–50% size reduction over JSON on the modes-heavy cosmology
frames; if `ormsgpack` isn't installed the protocol falls back to
JSON so unit tests can still run.
"""

from __future__ import annotations

import json
from typing import Any

from cosmic_forge_viz.schema import BaseFrame, frame_for_domain


def _try_ormsgpack() -> Any | None:
    try:
        import ormsgpack  # type: ignore[import-not-found]

        return ormsgpack
    except ImportError:
        return None


def encode_frame(frame: BaseFrame) -> bytes:
    """Serialize `frame` to msgpack bytes (or JSON if msgpack unavailable)."""
    payload = frame.model_dump(mode="json")
    om = _try_ormsgpack()
    if om is not None:
        return om.packb(payload, option=om.OPT_SERIALIZE_NUMPY)
    return json.dumps(payload).encode("utf-8")


def decode_frame(data: bytes) -> BaseFrame:
    """Parse `data` into the domain-typed frame the payload describes."""
    om = _try_ormsgpack()
    if om is not None:
        try:
            payload = om.unpackb(data)
        except Exception:
            payload = json.loads(data.decode("utf-8"))
    else:
        payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict) or "domain" not in payload:
        raise ValueError("decoded frame is missing required `domain` discriminator")
    cls = frame_for_domain(str(payload["domain"]))
    return cls.model_validate(payload)


def has_msgpack() -> bool:
    return _try_ormsgpack() is not None


__all__ = ["encode_frame", "decode_frame", "has_msgpack"]
