"""qfull-amo MUST NOT import from ucgle_f1 or other qfull_*."""

from __future__ import annotations

import pathlib
import re

PKG_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "qfull_amo"

_FORBIDDEN = re.compile(
    r"^\s*(from|import)\s+(ucgle_f1|qfull_(?!amo\b)[a-z_]+)\b",
    flags=re.MULTILINE,
)


def test_no_imports_from_ucglef1_or_other_qfull() -> None:
    offenders: list[str] = []
    for path in PKG_ROOT.rglob("*.py"):
        text = path.read_text()
        if _FORBIDDEN.search(text):
            offenders.append(str(path.relative_to(PKG_ROOT)))
    assert not offenders, f"qfull-amo boundary violated: {offenders}"
