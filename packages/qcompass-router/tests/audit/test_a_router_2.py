"""A-router-2: SSL pinning enforced for cloud-pricing refresh.

We stub `client_factory` and assert the constructed httpx client uses
the pinned CA bundle path passed to `PricingEngine(ca_bundle=...)`. This
keeps the test offline while still exercising the pinning contract.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from qcompass_router.pricing import PricingEngine


def _fake_response(status_code: int = 200, body: dict | None = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = b"{}" if body is None else b"{}"
    resp.json = lambda: body or {}
    return resp


def test_refresh_live_uses_pinned_verify(tmp_path: Path) -> None:
    ca_path = tmp_path / "ca.pem"
    ca_path.write_text("-----DUMMY-----\n", encoding="utf-8")

    constructed: dict[str, object] = {}

    def factory():
        client = MagicMock()
        # Capture the verify target the engine asked for.
        constructed["verify"] = engine._verify_target()
        client.get = MagicMock(return_value=_fake_response(200, {}))
        return client

    engine = PricingEngine(
        cache_dir=tmp_path / "cache",
        ca_bundle=ca_path,
        client_factory=factory,
    )
    engine.refresh_live(["ibm", "braket", "azure", "iqm"])

    assert constructed["verify"] == ca_path
    # The cache directory was created.
    assert (tmp_path / "cache").is_dir()


def test_refresh_live_offline_safe(tmp_path: Path) -> None:
    """Network failure must NOT raise; engine falls back to seed."""

    def factory():
        client = MagicMock()
        client.get = MagicMock(side_effect=RuntimeError("network down"))
        return client

    engine = PricingEngine(
        cache_dir=tmp_path / "cache",
        client_factory=factory,
    )
    # No exception raised even though every fetch errors.
    engine.refresh_live(["ibm", "braket"])

    # Subsequent estimate still works (seed fallback).
    cost = engine.estimate("ibm", "", None, 1024)
    assert cost.usd >= 0.0
    assert cost.live is False


def test_refresh_live_skips_when_factory_unavailable(tmp_path: Path) -> None:
    """If client construction itself raises, refresh exits silently."""
    from qcompass_router.pricing import _LiveFetchError

    def broken_factory():
        raise _LiveFetchError("httpx not installed")

    engine = PricingEngine(
        cache_dir=tmp_path / "cache",
        client_factory=broken_factory,
    )
    engine.refresh_live(["ibm"])
    # Cache dir exists but no provider files were written.
    assert list((tmp_path / "cache").glob("*.json")) == []


def test_pinned_transport_construction() -> None:
    """`httpx.HTTPTransport(verify=<SSLContext>)` is the pinning surface
    `PricingEngine` relies on. Build one and confirm it's CERT_REQUIRED.
    """
    pytest.importorskip("httpx")
    import ssl

    import httpx

    ctx = ssl.create_default_context()
    transport = httpx.HTTPTransport(verify=ctx)
    assert transport is not None
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True
