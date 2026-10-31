"""S-bench-3: render_markdown does not leak secrets."""

from __future__ import annotations

import os
from datetime import datetime

from qcompass_bench import BenchEntry, render_markdown


def test_render_markdown_redacts_api_token() -> None:
    secret = "sk-1234567890abcdef1234567890abcdef"
    entry = BenchEntry(
        domain="chemistry",
        fixture="h2",
        package_version="0.1.0",
        started_at=datetime.utcnow(),
        wall_seconds=0.123,
        classical_energy=-1.137,
        quantum_energy=None,
        provenance_hash=secret,  # contrived: pretend a hash leaked a key
        ok=True,
        notes=f"key {secret}",
    )
    text = render_markdown([entry])
    assert "[REDACTED]" in text
    assert secret not in text


def test_render_markdown_substitutes_home_dir() -> None:
    home = os.path.expanduser("~") or "/root"
    entry = BenchEntry(
        domain="chemistry",
        fixture="h2",
        package_version="0.1.0",
        started_at=datetime.utcnow(),
        wall_seconds=0.123,
        classical_energy=-1.137,
        quantum_energy=None,
        provenance_hash="abc",
        ok=True,
        notes=f"file {home}/secret/path",
    )
    text = render_markdown([entry])
    assert home not in text or home == "/"
    assert "~/" in text or "secret/path" not in text


def test_render_markdown_handles_empty() -> None:
    text = render_markdown([])
    assert "*No bench runs recorded yet.*" in text
