"""Pytest rootdir marker for qcompass-router tests.

Also re-exports the PROMPT 6A test double so the router-branch audit
tests' ``from tests.conftest import FakeAdapter`` resolves. The one
definition stays in ``tests/lineage_6a/conftest.py`` (kept verbatim
from main); it is loaded by path because ``lineage_6a`` is not a
package.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_LINEAGE_6A_CONFTEST = Path(__file__).resolve().parent / "lineage_6a" / "conftest.py"


def _load_lineage_6a_conftest():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(
        "qcompass_router_tests_lineage_6a_conftest", _LINEAGE_6A_CONFTEST,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_lineage_6a = _load_lineage_6a_conftest()
FakeAdapter = _lineage_6a.FakeAdapter
SMALL_QASM = _lineage_6a.SMALL_QASM
LARGE_QASM = _lineage_6a.LARGE_QASM

__all__ = ["LARGE_QASM", "SMALL_QASM", "FakeAdapter"]
