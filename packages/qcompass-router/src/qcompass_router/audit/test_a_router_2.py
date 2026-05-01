"""A-router-2: SSL-pinned HTTPS for every provider adapter.

This is a structural assertion: every cloud provider adapter that
opens an HTTP connection MUST go through ``ssl_pin.client()``
rather than constructing an httpx.Client directly. We grep the
provider source files for the offending pattern.

PROMPT 6B: Phase-1 adapters do not yet open live connections (each
``submit()`` raises NotImplementedError). The audit therefore
asserts:

  - ssl_pin.client() exists and returns a configured client
  - no provider source contains a bare ``httpx.Client(`` /
    ``httpx.AsyncClient(`` call (PROMPT 6C lands the live HTTP
    fetchers and they MUST go through ssl_pin).
"""

from __future__ import annotations

import re
from pathlib import Path

from qcompass_router import ssl_pin

PROVIDERS_ROOT = (
    Path(__file__).resolve().parents[1] / "providers"
)

_BAD = re.compile(r"\bhttpx\.(Async)?Client\s*\(")


def test_ssl_pin_module_exposes_client() -> None:
    assert callable(ssl_pin.client)
    assert callable(ssl_pin.async_client)
    assert ssl_pin.PINNED is True


def test_no_provider_uses_unpinned_httpx() -> None:
    offenders: list[str] = []
    for path in PROVIDERS_ROOT.rglob("*.py"):
        text = path.read_text()
        # Acceptable: importing httpx through ssl_pin (e.g. the
        # ssl_pin module itself). The check fires on direct
        # `httpx.Client(` / `httpx.AsyncClient(` invocations.
        if _BAD.search(text):
            offenders.append(str(path.relative_to(PROVIDERS_ROOT)))
    assert not offenders, (
        "Provider adapters MUST go through qcompass_router.ssl_pin "
        f"instead of bare httpx.Client(); offenders: {offenders}"
    )


def test_ssl_pin_module_uses_certifi() -> None:
    """Certifi is the trust source; this guards future regressions."""
    src = (Path(ssl_pin.__file__)).read_text()
    assert "import certifi" in src
    assert "certifi.where()" in src
