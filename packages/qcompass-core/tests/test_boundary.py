"""Boundary guard.

qcompass-core MUST NOT import from ucgle_f1 or any qfull_*. CI
enforces this with a grep, but we also assert at the test level so
local dev catches violations before push.
"""

from __future__ import annotations

import pathlib
import re

PKG_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "qcompass_core"

_FORBIDDEN = re.compile(
    r"^\s*(from|import)\s+(ucgle_f1|qfull_[a-z_]+)\b",
    flags=re.MULTILINE,
)


def test_no_imports_from_ucglef1_or_qfull() -> None:
    offenders: list[str] = []
    for path in PKG_ROOT.rglob("*.py"):
        text = path.read_text()
        if _FORBIDDEN.search(text):
            offenders.append(str(path.relative_to(PKG_ROOT)))
    assert not offenders, (
        f"qcompass-core must not import from ucgle_f1 or qfull_*; "
        f"offenders: {offenders}"
    )
