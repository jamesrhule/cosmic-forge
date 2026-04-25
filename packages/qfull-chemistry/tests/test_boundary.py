"""Boundary guard.

qfull-chemistry MUST NOT import from ucgle_f1 or any other qfull_*
sibling. CI also enforces this with a grep step (see ci.yml); this
test catches violations during local development.
"""

from __future__ import annotations

import pathlib
import re

PKG_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "qfull_chem"

# Match `from ucgle_f1...` or `import ucgle_f1...` plus any qfull_*
# sibling other than this package itself (qfull_chem).
_FORBIDDEN = re.compile(
    r"^\s*(from|import)\s+(ucgle_f1|qfull_(?!chem\b)[a-z_]+)\b",
    flags=re.MULTILINE,
)


def test_no_imports_from_ucglef1_or_other_qfull() -> None:
    offenders: list[str] = []
    for path in PKG_ROOT.rglob("*.py"):
        text = path.read_text()
        if _FORBIDDEN.search(text):
            offenders.append(str(path.relative_to(PKG_ROOT)))
    assert not offenders, (
        f"qfull-chemistry must not import from ucgle_f1 or other qfull_*; "
        f"offenders: {offenders}"
    )
