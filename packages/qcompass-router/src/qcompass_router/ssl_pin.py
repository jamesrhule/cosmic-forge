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

from typing import Any

# Module-level fallback flag so test_a_router_2 can detect the
# ssl_pin import contract even if httpx + certifi are not installed
# in a minimal environment.
PINNED = True


def client(**httpx_kwargs: Any) -> Any:
    """Return a configured ``httpx.Client``.

    The keyword arguments override our defaults except ``verify``,
    which we always set to the certifi bundle.
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

    httpx_kwargs.pop("verify", None)
    return httpx.Client(verify=certifi.where(), **httpx_kwargs)


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
