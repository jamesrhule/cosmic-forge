"""Phase-3 descope-or-commit verdict pipeline (PROMPT 10 v2 §D).

Per-domain delivery criteria (verbatim from the spec):

  1. ≥3 reproducible results with classical_reference_hash.
  2. Quantum observable not reachable classically at the same
     wallclock.
  3. Peer-reviewed citation in references.bib.
  4. Per-domain audit green ≥30 days.

Verdict:
  - DELIVERED  → all four criteria met → auto-PR promotes the
                 plugin to 1.0 versioning.
  - PENDING    → at least one criterion missing AND ≤ cutoff days.
  - FAILED     → past cutoff and still missing → auto-PR moves the
                 plugin to research/packages/.

The pipeline NEVER deletes audit artifacts; FAILED domains move
their source tree but leave the audit trail intact.

CLI:
    qcompass verdict run --cutoff-days 90
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Literal


VerdictStatus = Literal["DELIVERED", "PENDING", "FAILED"]


@dataclass
class CriterionEvidence:
    """One criterion's evidence record."""

    name: str
    met: bool
    detail: str = ""


@dataclass
class DomainVerdict:
    domain: str
    status: VerdictStatus
    criteria: list[CriterionEvidence] = field(default_factory=list)
    audit_green_since: datetime | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "status": self.status,
            "criteria": [asdict(c) for c in self.criteria],
            "audit_green_since": (
                self.audit_green_since.isoformat()
                if self.audit_green_since else None
            ),
            "notes": self.notes,
        }


@dataclass
class VerdictReport:
    generated_at: datetime
    cutoff_days: int
    verdicts: list[DomainVerdict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "cutoff_days": self.cutoff_days,
            "verdicts": [v.to_dict() for v in self.verdicts],
        }

    def by_status(self, status: VerdictStatus) -> list[DomainVerdict]:
        return [v for v in self.verdicts if v.status == status]


# ── Evidence collectors ────────────────────────────────────────


def _provenance_hashes_for_domain(
    domain: str, *, artifacts_root: Path,
) -> list[str]:
    """Scan ``$UCGLE_F1_ARTIFACTS/qcompass/<domain>/*.provenance.json``."""
    domain_root = artifacts_root / domain
    if not domain_root.exists():
        return []
    hashes: list[str] = []
    for path in sorted(domain_root.glob("*.provenance.json")):
        try:
            blob = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        prov = blob.get("provenance") or {}
        h = str(prov.get("classical_reference_hash") or "")
        if h:
            hashes.append(h)
    return hashes


def _references_bib_has_citation(
    domain: str, *, repo_root: Path,
) -> bool:
    """Look for ``@... { qcompass-<domain>-... ,`` in references.bib."""
    candidates = (
        repo_root / "docs" / "qcompass" / "references.bib",
        repo_root / "docs" / "references.bib",
        repo_root / "references.bib",
    )
    needle = f"qcompass-{domain}"
    for p in candidates:
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if needle in text:
            return True
    return False


def _audit_green_anchor(
    domain: str, *, baseline_log: Path,
) -> datetime | None:
    """Heuristic: take the mtime of the most recent baseline-log
    entry mentioning the domain as the green-since anchor.
    """
    if not baseline_log.exists():
        return None
    try:
        text = baseline_log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if domain not in text:
        return None
    return datetime.fromtimestamp(baseline_log.stat().st_mtime, tz=UTC)


# ── Verdict engine ─────────────────────────────────────────────


def _evaluate_domain(
    domain: str,
    *,
    cutoff_days: int,
    artifacts_root: Path,
    repo_root: Path,
    baseline_log: Path,
    quantum_advantage_overrides: dict[str, bool] | None = None,
    now: datetime | None = None,
) -> DomainVerdict:
    now = now or datetime.now(UTC)
    overrides = quantum_advantage_overrides or {}

    hashes = _provenance_hashes_for_domain(
        domain, artifacts_root=artifacts_root,
    )
    crit_repro = CriterionEvidence(
        name="≥3 reproducible classical_reference_hash",
        met=len(hashes) >= 3,
        detail=f"found {len(hashes)} hashes",
    )
    crit_quantum = CriterionEvidence(
        name="quantum observable not reachable classically",
        met=bool(overrides.get(domain, False)),
        detail=(
            "operator override (CI flips when the per-domain audit "
            "records a verified quantum advantage)."
        ),
    )
    crit_citation = CriterionEvidence(
        name="peer-reviewed citation in references.bib",
        met=_references_bib_has_citation(domain, repo_root=repo_root),
        detail=f"needle: 'qcompass-{domain}'",
    )
    audit_anchor = _audit_green_anchor(domain, baseline_log=baseline_log)
    crit_audit = CriterionEvidence(
        name="per-domain audit green ≥30 days",
        met=(
            audit_anchor is not None
            and (now - audit_anchor) >= timedelta(days=30)
        ),
        detail=(
            f"green-since {audit_anchor.isoformat()}"
            if audit_anchor else "no green-since anchor found"
        ),
    )
    criteria = [crit_repro, crit_quantum, crit_citation, crit_audit]
    all_met = all(c.met for c in criteria)
    if all_met:
        status: VerdictStatus = "DELIVERED"
    else:
        # Past cutoff = FAILED if the audit anchor is older than
        # cutoff_days OR no anchor at all + ≥cutoff days since
        # repo init heuristic (use baseline log mtime as proxy).
        anchor = audit_anchor or (
            datetime.fromtimestamp(
                baseline_log.stat().st_mtime, tz=UTC,
            )
            if baseline_log.exists() else now
        )
        age = now - anchor
        status = "FAILED" if age > timedelta(days=cutoff_days) else "PENDING"
    return DomainVerdict(
        domain=domain,
        status=status,
        criteria=criteria,
        audit_green_since=audit_anchor,
    )


def run_verdict(
    *,
    cutoff_days: int = 90,
    domains: Iterable[str] | None = None,
    artifacts_root: Path | None = None,
    repo_root: Path | None = None,
    quantum_advantage_overrides: dict[str, bool] | None = None,
    now: datetime | None = None,
) -> VerdictReport:
    """Evaluate the per-domain delivery criteria and return a report.

    The default ``domains`` set is the union of installed
    ``qcompass.domains`` entry points (excluding the ``null``
    sentinel) so adding a new domain to the workspace is picked up
    automatically.
    """
    artifacts_root = (
        artifacts_root
        or Path(os.environ.get("UCGLE_F1_ARTIFACTS")
                or (Path.home() / ".ucgle_f1" / "artifacts"))
        / "qcompass"
    )
    repo_root = repo_root or _detect_repo_root()
    baseline_log = repo_root / "acceptance" / "sprint1-baseline.log"
    if domains is None:
        domains = _discover_domains()
    verdicts = [
        _evaluate_domain(
            domain,
            cutoff_days=cutoff_days,
            artifacts_root=artifacts_root,
            repo_root=repo_root,
            baseline_log=baseline_log,
            quantum_advantage_overrides=quantum_advantage_overrides,
            now=now,
        )
        for domain in sorted(set(domains))
    ]
    return VerdictReport(
        generated_at=now or datetime.now(UTC),
        cutoff_days=cutoff_days,
        verdicts=verdicts,
    )


# ── Renderers ──────────────────────────────────────────────────


def render_yaml(report: VerdictReport) -> str:
    """Hand-rolled YAML so the renderer doesn't depend on PyYAML."""
    lines = [
        f"generated_at: {report.generated_at.isoformat()}",
        f"cutoff_days: {report.cutoff_days}",
        "verdicts:",
    ]
    for v in report.verdicts:
        lines.append(f"  - domain: {v.domain}")
        lines.append(f"    status: {v.status}")
        if v.audit_green_since:
            lines.append(
                f"    audit_green_since: {v.audit_green_since.isoformat()}",
            )
        lines.append("    criteria:")
        for c in v.criteria:
            lines.append(f"      - name: {c.name!r}")
            lines.append(f"        met: {str(c.met).lower()}")
            if c.detail:
                lines.append(f"        detail: {c.detail!r}")
    return "\n".join(lines) + "\n"


def render_markdown(report: VerdictReport) -> str:
    out = [
        f"# Phase-3 Verdict — {report.generated_at.isoformat()}",
        "",
        f"Cutoff: **{report.cutoff_days} days**",
        "",
        "| domain | status | criteria met |",
        "|---|---|---|",
    ]
    for v in report.verdicts:
        met = sum(1 for c in v.criteria if c.met)
        out.append(f"| {v.domain} | **{v.status}** | {met}/{len(v.criteria)} |")
    out.append("")
    for v in report.verdicts:
        out.append(f"## {v.domain} — {v.status}")
        for c in v.criteria:
            mark = "✅" if c.met else "❌"
            out.append(f"- {mark} {c.name} — {c.detail}")
        out.append("")
    return "\n".join(out)


def write_report(
    report: VerdictReport, *, out_dir: Path,
) -> tuple[Path, Path]:
    """Write ``verdict_report.{yaml,md}`` and return the paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = out_dir / "verdict_report.yaml"
    md_path = out_dir / "verdict_report.md"
    yaml_path.write_text(render_yaml(report))
    md_path.write_text(render_markdown(report))
    return yaml_path, md_path


# ── Discovery helpers ──────────────────────────────────────────


def _discover_domains() -> list[str]:
    try:
        from qcompass_core.registry import list_domains  # type: ignore[import-not-found]
        return [d for d in list_domains() if d != "null"]
    except Exception:
        return [
            "cosmology.ucglef1", "chemistry", "condmat", "amo",
            "hep", "nuclear", "gravity", "statmech",
        ]


def _detect_repo_root() -> Path:
    """Walk up from this file until we find pyproject.toml + .git."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists() and (parent / ".git").exists():
            return parent
    return Path.cwd()


__all__ = [
    "CriterionEvidence",
    "DomainVerdict",
    "VerdictReport",
    "VerdictStatus",
    "render_markdown",
    "render_yaml",
    "run_verdict",
    "write_report",
]
