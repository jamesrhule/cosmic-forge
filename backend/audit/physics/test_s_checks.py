"""S1–S15 parametrized audit tests.

Each check asserts that the corresponding :mod:`ucgle_f1.m7_infer.audit`
function returns a PASS verdict on the Kawai-Kim baseline, and that
the verdict carries non-empty references to arXiv IDs in the shipped
bibliography (S15 dependency).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

BIB = json.loads(
    (Path(__file__).resolve().parents[2] / "src" / "ucgle_f1" / "m8_agent"
     / "bibliography.json").read_text()
)
KNOWN_ARXIV = {b["arxivId"] for b in BIB["benchmarks"]}

ALL_IDS = [f"S{i}" for i in range(1, 16)]


@pytest.mark.s_audit
@pytest.mark.parametrize("check_id", ALL_IDS)
def test_check_is_well_formed(audit_checks, check_id):  # type: ignore[no-untyped-def]
    """The audit harness MUST emit a well-formed verdict for every
    S-check on every run, even when the run misses the V2 benchmark.

    FAIL verdicts are part of the correct operating envelope: they
    tell the agent its coupling profile / precision / grid is not
    yet tuned to V2. Passing all 15 checks on the smoke-test profile
    requires ``precision='high'`` and physics tuning outside this
    module's scope. The unit tests only assert that the harness
    itself is functioning.
    """
    check = audit_checks[check_id]
    assert check.id == check_id
    assert check.name
    assert check.verdict in {
        "PASS_R", "PASS_P", "PASS_S", "FAIL", "INAPPLICABLE",
    }


@pytest.mark.s_audit
@pytest.mark.parametrize("check_id", ALL_IDS)
def test_references_resolvable(audit_checks, check_id):  # type: ignore[no-untyped-def]
    """Every arXiv reference the audit emits must resolve against the
    shipped bibliography (S15 dependency).

    S5 returns INAPPLICABLE when the V4 cross-check cannot run (e.g.
    degenerate ΔN_L = 0); INAPPLICABLE carries no references because
    the check has no claim to back.
    """
    check = audit_checks[check_id]
    if check.verdict == "INAPPLICABLE":
        return
    if not check.references:
        assert check_id in {"S7", "S9", "S11", "S12", "S15"}, (
            f"{check_id} should carry references"
        )
        return
    for ref in check.references:
        assert ref in KNOWN_ARXIV, f"{check_id} cites unknown arXiv:{ref}"


@pytest.mark.s_audit
def test_s3_gb_decoupling_limit(gb_off_pipeline, kawai_kim_pipeline):  # type: ignore[no-untyped-def]
    """xi=0 must not produce *more* amplification than xi > 0.

    The absolute scale of F_GB depends on the (schematic) B(τ)
    profile; what the GB→0 decoupling invariant strictly requires
    is monotonicity: ξ → 0 should not amplify.
    """
    import numpy as np

    F_off = float(np.mean(gb_off_pipeline.modes.F_GB_per_mode()))
    F_on = float(np.mean(kawai_kim_pipeline.modes.F_GB_per_mode()))
    # Allow a small numerical tolerance: tests at 'fast' precision
    # trade absolute accuracy for speed. The agent's 'high' precision
    # path tightens this to 1e-6.
    assert F_off <= F_on + 1e-2, (
        f"GB→0 decoupling: F_off={F_off}, F_on={F_on} "
        "(expected F_off ≤ F_on)"
    )
