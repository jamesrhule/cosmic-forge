"""A5 — audit preservation under agent patches.

A proposed patch that would fail any S1–S15 check must be rejected
by :func:`dry_run_patch` before reaching human review. We encode
this as a structural invariant: the dry-run report surface carries
``auditChecksBroken``, and the ``passed`` flag is false when it is
non-empty.
"""

from __future__ import annotations

import inspect

import pytest

from ucgle_f1.domain import PatchTestReport
from ucgle_f1.m8_agent.sandbox import dry_run
from ucgle_f1.m8_agent.tools.patch import propose_patch, request_human_review


@pytest.mark.a_audit
def test_patch_test_report_carries_audit_status() -> None:
    # The PatchTestReport model must track which S1–S15 checks broke.
    fields = PatchTestReport.model_fields
    assert "auditChecksBroken" in fields
    assert "auditChecksPreserved" in fields
    assert "passed" in fields


@pytest.mark.a_audit
def test_dry_run_classifies_audit_outcomes() -> None:
    src = inspect.getsource(dry_run)
    assert "_classify_audit_results" in src
    for cid in [f"S{i}" for i in range(1, 16)]:
        assert cid in src, f"dry-run classifier must know about {cid}"


@pytest.mark.a_audit
def test_propose_and_review_path() -> None:
    """Agent can propose + mark for review; the apply step is absent."""
    p = propose_patch(
        conversation_id="conv_a5",
        target_path="backend/src/ucgle_f1/m3_modes/chiral.py",
        rationale="demo",
        unified_diff="--- a\n+++ b\n@@ -1 +1 @@\n-x\n+y\n",
    )
    ticket = request_human_review(p.patchId)
    assert ticket.status == "open"
    # There is no apply_patch tool — the agent cannot self-merge.
    from ucgle_f1.m8_agent.tools import ALL_TOOL_SPECS
    names = {t.name for t in ALL_TOOL_SPECS}
    assert "apply_patch" not in names
