"""Phase-3 verdict pipeline tests (PROMPT 10 v2 §D)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qcompass_bench.phase3_verdict import (
    CriterionEvidence,
    DomainVerdict,
    VerdictReport,
    render_markdown,
    render_yaml,
    run_verdict,
    write_report,
)


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Build a tiny fake repo root with the structure the verdict reads."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("# fake\n")
    (tmp_path / "acceptance").mkdir()
    (tmp_path / "acceptance" / "sprint1-baseline.log").write_text(
        "PROMPT 0..10 v2 — chemistry / cosmology / hep / nuclear all green.\n",
    )
    (tmp_path / "docs" / "qcompass").mkdir(parents=True)
    (tmp_path / "docs" / "qcompass" / "references.bib").write_text(
        "@article{qcompass-chemistry-h2-2024, title={H2 ref}}\n"
        "@article{qcompass-hep-schwinger-2024, title={Schwinger ref}}\n",
    )
    return tmp_path


@pytest.fixture
def fake_artifacts(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts" / "qcompass"
    root.mkdir(parents=True)
    return root


def _seed_provenance(
    artifacts_root: Path, domain: str, *, n: int, seed: str = "deadbeef",
) -> None:
    domain_dir = artifacts_root / domain
    domain_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        sidecar = domain_dir / f"qc_{domain}_{i:04d}.provenance.json"
        sidecar.write_text(json.dumps({
            "schemaVersion": 1,
            "runId": f"qc_{domain}_{i:04d}",
            "domain": domain,
            "manifest": {},
            "provenance": {
                "classical_reference_hash": f"{seed}{i:04d}",
                "calibration_hash": None,
                "error_mitigation": None,
            },
        }))


def test_pending_verdict_when_no_artifacts(
    fake_repo: Path, fake_artifacts: Path,
) -> None:
    report = run_verdict(
        cutoff_days=90,
        domains=["chemistry"],
        artifacts_root=fake_artifacts,
        repo_root=fake_repo,
    )
    assert len(report.verdicts) == 1
    v = report.verdicts[0]
    assert v.domain == "chemistry"
    assert v.status in {"PENDING", "FAILED"}
    assert any("≥3" in c.name for c in v.criteria)


def test_delivered_verdict_when_all_criteria_met(
    fake_repo: Path, fake_artifacts: Path,
) -> None:
    _seed_provenance(fake_artifacts, "chemistry", n=4)
    # Force the audit-green anchor to be > 30 days old by predating
    # the baseline log.
    log = fake_repo / "acceptance" / "sprint1-baseline.log"
    old = (datetime.now(UTC) - timedelta(days=45)).timestamp()
    log.write_text("chemistry green for 45+ days\n")
    import os
    os.utime(log, (old, old))
    report = run_verdict(
        cutoff_days=90,
        domains=["chemistry"],
        artifacts_root=fake_artifacts,
        repo_root=fake_repo,
        quantum_advantage_overrides={"chemistry": True},
    )
    v = report.verdicts[0]
    assert v.status == "DELIVERED", v.criteria


def test_failed_verdict_when_past_cutoff(
    fake_repo: Path, fake_artifacts: Path,
) -> None:
    log = fake_repo / "acceptance" / "sprint1-baseline.log"
    old = (datetime.now(UTC) - timedelta(days=400)).timestamp()
    log.write_text("nuclear was green long ago\n")
    import os
    os.utime(log, (old, old))
    report = run_verdict(
        cutoff_days=90,
        domains=["nuclear"],
        artifacts_root=fake_artifacts,
        repo_root=fake_repo,
    )
    v = report.verdicts[0]
    assert v.status == "FAILED"


def test_render_yaml_emits_canonical_keys(
    fake_repo: Path, fake_artifacts: Path,
) -> None:
    report = run_verdict(
        cutoff_days=90,
        domains=["chemistry"],
        artifacts_root=fake_artifacts,
        repo_root=fake_repo,
    )
    yaml_text = render_yaml(report)
    for needle in ("generated_at:", "cutoff_days:", "verdicts:", "status:"):
        assert needle in yaml_text


def test_render_markdown_lists_per_domain(
    fake_repo: Path, fake_artifacts: Path,
) -> None:
    report = run_verdict(
        cutoff_days=90,
        domains=["chemistry", "hep"],
        artifacts_root=fake_artifacts,
        repo_root=fake_repo,
    )
    md = render_markdown(report)
    assert "# Phase-3 Verdict" in md
    assert "## chemistry" in md
    assert "## hep" in md


def test_write_report_creates_both_files(
    fake_repo: Path, fake_artifacts: Path, tmp_path: Path,
) -> None:
    report = run_verdict(
        cutoff_days=90,
        domains=["chemistry"],
        artifacts_root=fake_artifacts,
        repo_root=fake_repo,
    )
    yaml_path, md_path = write_report(report, out_dir=tmp_path / "verdict")
    assert yaml_path.exists()
    assert md_path.exists()


def test_verdict_pipeline_never_deletes_audit_artifacts(
    fake_repo: Path, fake_artifacts: Path,
) -> None:
    """RULES: 'Verdict pipeline NEVER deletes audit artifacts; archive only.'

    The pipeline is read-only against the artifacts root. Run it
    on a populated tree and verify file count is unchanged.
    """
    _seed_provenance(fake_artifacts, "chemistry", n=4)
    before = sorted(p.name for p in (fake_artifacts / "chemistry").iterdir())
    run_verdict(
        cutoff_days=90,
        domains=["chemistry"],
        artifacts_root=fake_artifacts,
        repo_root=fake_repo,
    )
    after = sorted(p.name for p in (fake_artifacts / "chemistry").iterdir())
    assert before == after


def test_quantum_advantage_override_flips_criterion(
    fake_repo: Path, fake_artifacts: Path,
) -> None:
    _seed_provenance(fake_artifacts, "chemistry", n=4)
    report_no_override = run_verdict(
        cutoff_days=90,
        domains=["chemistry"],
        artifacts_root=fake_artifacts,
        repo_root=fake_repo,
    )
    report_with_override = run_verdict(
        cutoff_days=90,
        domains=["chemistry"],
        artifacts_root=fake_artifacts,
        repo_root=fake_repo,
        quantum_advantage_overrides={"chemistry": True},
    )
    qa_no = next(
        c for c in report_no_override.verdicts[0].criteria
        if "quantum" in c.name
    )
    qa_yes = next(
        c for c in report_with_override.verdicts[0].criteria
        if "quantum" in c.name
    )
    assert qa_no.met is False
    assert qa_yes.met is True
