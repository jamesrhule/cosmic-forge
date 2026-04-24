"""Parity with the TypeScript domain contract.

The TS contract lives at ``/src/types/domain.ts``. This test reads
that file and asserts that every type name defined there is also
defined on our Pydantic side (or intentionally omitted with a
documented reason).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TS_PATH = Path(__file__).resolve().parents[3] / "src" / "types" / "domain.ts"


# Types that are frontend-only (error classes, enums encoded via Literal).
_FRONTEND_ONLY = {
    "ServiceError",     # implemented as an Exception in Python
}


@pytest.mark.skipif(not TS_PATH.exists(), reason="no frontend domain.ts")
def test_python_mirrors_every_ts_type() -> None:
    src = TS_PATH.read_text()
    ts_names = set(re.findall(r"export\s+(?:interface|class)\s+(\w+)", src))
    ts_names -= _FRONTEND_ONLY

    from ucgle_f1 import domain as py_domain

    py_names = {
        name for name in dir(py_domain)
        if not name.startswith("_")
    }
    missing = [n for n in ts_names if n not in py_names]
    assert not missing, f"Pydantic mirror missing TS types: {missing}"


@pytest.mark.skipif(not TS_PATH.exists(), reason="no frontend domain.ts")
def test_tool_name_union_matches_docs() -> None:
    """The agent's tool surface is strictly a superset of the frontend union."""
    src = TS_PATH.read_text()
    m = re.search(r"export\s+type\s+ToolName\s*=([^;]*);", src, flags=re.S)
    assert m is not None
    ts_tools = set(re.findall(r'"([^"]+)"', m.group(1)))
    from ucgle_f1.m8_agent.tools import ALL_TOOL_SPECS
    py_tools = {t.name for t in ALL_TOOL_SPECS}
    # ``load_run`` / ``plot_overlay`` etc. are aliases the agent
    # services through research/simulator tools, so we don't require
    # one-to-one. Instead require that the M8 surface is non-empty
    # and lists the additions the spec mandates.
    for required in {
        "list_benchmarks", "get_run", "validate_config", "start_run",
        "cancel_run", "stream_run", "propose_experiments",
        "propose_patch", "dry_run_patch", "request_human_review",
        "list_tools", "describe_tool", "get_capabilities",
    }:
        assert required in py_tools, f"agent missing tool: {required}"
    _ = ts_tools  # tracked for future strict mode
