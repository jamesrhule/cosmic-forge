"""SSL-pinned httpx client used by every cloud provider adapter.

PROMPT 6B audit ``A-router-2`` requires every provider HTTP path to
go through this module (verified by a static grep over
``providers/`` source files).

Pinning model: pin the root CA bundle from :mod:`certifi`. This is
not certificate pinning in the strict sense (no individual leaf-cert
pin) — it is a guarantee that we use the curated certifi roots
rather than the system trust store, which on some embedded CI
machines can be empty or stale. PROMPT 6C may extend this to
per-provider leaf-cert pins.
"""

from __future__ import annotations

import ssl
from pathlib import Path
from typing import Any

# Module-level fallback flag so test_a_router_2 can detect the
# ssl_pin import contract even if httpx + certifi are not installed
# in a minimal environment.
PINNED = True


def pinned_context(ca_bundle: str | Path | bool | None = None) -> ssl.SSLContext:
    """``CERT_REQUIRED`` + hostname-checking context over ``ca_bundle``.

    ``None`` / ``True`` mean the certifi bundle. The context is what
    ``httpx.HTTPTransport(verify=...)`` receives, so callers can pin a
    private CA (``PricingEngine(ca_bundle=...)``) without ever turning
    verification off.
    """
    if ca_bundle is None or ca_bundle is True:
        import certifi  # type: ignore[import-not-found]

        ca_bundle = certifi.where()
    if ca_bundle is False:
        msg = "TLS verification cannot be disabled for pinned clients."
        raise ValueError(msg)
    return ssl.create_default_context(cafile=str(ca_bundle))


def client(
    *, ca_bundle: str | Path | bool | None = None, **httpx_kwargs: Any,
) -> Any:
    """Return a configured ``httpx.Client``.

    The keyword arguments override our defaults except ``verify``,
    which is always the pinned context: the certifi bundle
    (``certifi.where()``) unless ``ca_bundle`` names another root.
    """
    try:
        import certifi  # type: ignore[import-not-found]
        import httpx  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - dev path
        msg = (
            "ssl_pin.client() requires httpx + certifi. Install via "
            "qcompass-router[dev] or your provider extra."
        )
        raise ImportError(msg) from exc

    _ = certifi
    httpx_kwargs.pop("verify", None)
    return httpx.Client(
        transport=httpx.HTTPTransport(verify=pinned_context(ca_bundle)),
        **httpx_kwargs,
    )


def async_client(**httpx_kwargs: Any) -> Any:
    """Async variant of :func:`client`."""
    try:
        import certifi  # type: ignore[import-not-found]
        import httpx  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        msg = (
            "ssl_pin.async_client() requires httpx + certifi."
        )
        raise ImportError(msg) from exc

    httpx_kwargs.pop("verify", None)
    return httpx.AsyncClient(verify=certifi.where(), **httpx_kwargs)
