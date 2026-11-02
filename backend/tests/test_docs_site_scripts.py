"""Gate 1 round 3B (OPS2, LOW): the published docs site loads no script from a
compromised domain and no script at a moving version.

At 15e4e3c mkdocs.yml put https://polyfill.io/v3/polyfill.min.js (the domain
taken over in the 2024 polyfill.io supply-chain attack) and
https://cdn.jsdelivr.net/npm/mathjax@3/... (whatever 3.x is newest) on every
page of the site that release-please's publish-docs job deploys, so whoever
controlled either could run script in the docs origin for every visitor.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

REPO = Path(__file__).resolve().parents[2]
MKDOCS = REPO / "mkdocs.yml"

# Domains of the June 2024 polyfill.io supply-chain incident (the same
# operator served the injected script from each).
COMPROMISED = (
    "polyfill.io",
    "polyfill.com",
    "polyfillcache.com",
    "bootcss.com",
    "bootcdn.net",
    "staticfile.org",
    "staticfile.net",
)
# A CDN URL must name an exact npm release: /npm/<package>@<x.y.z>/<file>.
PINNED_NPM = re.compile(r"^/npm/(?:@[a-z0-9._-]+/)?[a-z0-9._-]+@\d+\.\d+\.\d+/[^@]+$")
ALLOWED_HOSTS = {"cdn.jsdelivr.net"}


def _config() -> dict[str, Any]:
    return yaml.safe_load(MKDOCS.read_text(encoding="utf-8"))


def _assets(config: dict[str, Any]) -> list[str]:
    out = []
    for key in ("extra_javascript", "extra_css"):
        for entry in config.get(key) or []:
            out.append(entry["path"] if isinstance(entry, dict) else str(entry))
    return out


def test_site_scripts_come_from_no_compromised_domain() -> None:
    for url in _assets(_config()):
        host = (urlsplit(url).hostname or "").lower()
        assert not any(host == d or host.endswith("." + d) for d in COMPROMISED), url


def test_every_remote_site_asset_is_an_exact_release() -> None:
    config = _config()
    docs_dir = REPO / config.get("docs_dir", "docs")
    for url in _assets(config):
        parts = urlsplit(url)
        if not parts.scheme and not parts.netloc:
            assert (docs_dir / url).is_file(), f"local asset missing: {url}"
            continue
        assert parts.scheme == "https", url
        assert parts.hostname in ALLOWED_HOSTS, f"script host not allowed: {url}"
        assert PINNED_NPM.match(parts.path), f"not an exact npm version: {url}"
        assert not parts.query, f"a query can change what the CDN serves: {url}"


def test_mathjax_is_pinned_to_the_verified_release() -> None:
    """3.2.2 is the newest 3.x on npm (Apache-2.0, published 2022-06-08);
    the URL keeps the es5 combined component the site used."""
    scripts = [u for u in _assets(_config()) if "mathjax" in u]
    assert scripts == ["https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js"]


def test_docs_pages_embed_no_remote_script() -> None:
    config = _config()
    docs_dir = REPO / config.get("docs_dir", "docs")
    for page in docs_dir.rglob("*"):
        if page.suffix in {".md", ".html"}:
            text = page.read_text(encoding="utf-8")
            assert not re.search(r"<script[^>]+src=[\"']?https?:", text, re.I), page
