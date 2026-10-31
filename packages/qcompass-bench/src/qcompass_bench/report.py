"""Markdown leaderboard rendering.

Renders the bench store contents as a leaderboard table. The
S-bench-3 audit asserts the renderer never leaks secrets — env
vars, file paths under ``~/``, or strings that look like API
tokens are scrubbed before output.
"""

from __future__ import annotations

import os
import re
from typing import Iterable

from .store import BenchEntry


_SECRET_LIKE = re.compile(
    r"(sk-[A-Za-z0-9]{16,}|gh[oprsu]_[A-Za-z0-9_]{16,}|"
    r"AKIA[0-9A-Z]{16}|"
    r"AIza[0-9A-Za-z_\-]{16,})"
)


def render_markdown(entries: Iterable[BenchEntry]) -> str:
    rows = list(entries)
    if not rows:
        return "*No bench runs recorded yet.*"
    header = (
        "| Domain | Fixture | Version | Wall (s) | Classical | "
        "Quantum | OK | Hash | Notes |\n"
        "|---|---|---|---|---|---|---|---|---|"
    )
    lines = [header]
    for r in rows:
        lines.append(
            f"| {r.domain} | {r.fixture} | {r.package_version} | "
            f"{r.wall_seconds:.3f} | {_fmt(r.classical_energy)} | "
            f"{_fmt(r.quantum_energy)} | {'✓' if r.ok else '✗'} | "
            f"{_truncate(r.provenance_hash, 16)} | "
            f"{_truncate(r.notes, 80)} |"
        )
    text = "\n".join(lines)
    return _scrub_secrets(text)


def _truncate(s: str, n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[: n - 1] + "…"


def _fmt(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.6g}"


def _scrub_secrets(text: str) -> str:
    text = _SECRET_LIKE.sub("[REDACTED]", text)
    home = os.path.expanduser("~")
    if home and home != "/":
        text = text.replace(home, "~")
    return text
