"""A2 — citation integrity.

Every arXiv ID referenced by an S-check or cited in a LiteratureSummary
must be resolvable against the shipped bibliography.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ucgle_f1.domain import ServiceError
from ucgle_f1.m8_agent.tools.research import cite_paper, summarize_literature

BIB_PATH = Path(__file__).resolve().parents[2] / "src" / "ucgle_f1" / "m8_agent" / "bibliography.json"
BIB = json.loads(BIB_PATH.read_text())


@pytest.mark.a_audit
def test_all_audit_refs_resolvable() -> None:
    known = {b["arxivId"] for b in BIB["benchmarks"]}
    for entry in BIB["audit"]:
        for ref in entry["refs"]:
            assert ref in known, f"{entry['id']} cites unknown {ref}"


@pytest.mark.a_audit
def test_cite_paper_valid() -> None:
    rec = cite_paper("1702.07689")
    assert rec.arxivId == "1702.07689"
    assert "V2" in rec.references


@pytest.mark.a_audit
def test_cite_paper_rejects_unknown() -> None:
    with pytest.raises(ServiceError):
        cite_paper("0000.00000")


@pytest.mark.a_audit
def test_summarize_literature_returns_known_ids() -> None:
    summary = summarize_literature("leptogenesis", k=3)
    assert summary.entries
    known = {b["arxivId"] for b in BIB["benchmarks"]}
    for e in summary.entries:
        assert e.arxivId in known
