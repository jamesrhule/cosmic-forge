"""Gate 1 round 3B (OPS2): ci.yml runs only actions pinned to a commit.

At 15e4e3c every action in ci.yml was referenced by a moving major tag
(actions/checkout@v4, oven-sh/setup-bun@v2, ...; dependency-review-action's
v4 is even a branch), so whoever could move one of those refs could run code
in every CI job, including the required checks and the jobs that hold
LHCI_GITHUB_APP_TOKEN or a pull-requests: write token. setup-bun also
restored the bun binary from an Actions cache that CI jobs running
lifecycle scripts could write. The pins are the commits those tags pointed
at (resolved with git ls-remote); job names, steps and the dependency-review
settings are unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"
CI = WORKFLOWS / "ci.yml"
PINNED_LINE = re.compile(r"(-\s+)?uses:\s*([\w.-]+/[\w./-]+)@([0-9a-f]{40}) # (v\d+\.\d+\.\d+)")


def _ci() -> dict[str, Any]:
    return yaml.safe_load(CI.read_text(encoding="utf-8"))


def _uses_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [ln.strip() for ln in text.splitlines() if re.match(r"\s*(-\s+)?uses:", ln)]


def test_every_ci_action_is_pinned_to_a_commit_with_its_release() -> None:
    lines = _uses_lines(CI)
    assert lines
    for line in lines:
        assert PINNED_LINE.fullmatch(line), f"not pinned to a full commit SHA with # vX.Y.Z: {line}"


def test_one_release_is_one_commit_across_the_pinned_workflows() -> None:
    """The same action at the same release has the same SHA everywhere."""
    seen: dict[tuple[str, str], set[str]] = {}
    for name in ("ci.yml", "deploy.yml", "release-please.yml"):
        for line in _uses_lines(WORKFLOWS / name):
            m = PINNED_LINE.fullmatch(line)
            if m:
                seen.setdefault((m.group(2), m.group(4)), set()).add(m.group(3))
    for (action, release), shas in seen.items():
        assert len(shas) == 1, f"{action} {release} pinned to {shas}"


def test_setup_bun_never_restores_bun_from_a_cache_in_ci() -> None:
    for job_id, job in _ci()["jobs"].items():
        for st in job.get("steps", []):
            if str(st.get("uses", "")).startswith("oven-sh/setup-bun@"):
                assert st["with"].get("no-cache") is True, f"{job_id}: setup-bun restores a cache"
                assert st["with"].get("bun-version") == "${{ env.BUN_VERSION }}", job_id


def test_jobs_and_dependency_review_settings_are_unchanged() -> None:
    ci = _ci()
    names = {job_id: job.get("name") for job_id, job in ci["jobs"].items()}
    assert names == {
        "secrets": "secrets (gitleaks)",
        "dependency-review": "dependency review",
        "licences": "licence gate",
        "frontend": "frontend (lint · format · types · vitest · build · audit)",
        "ssr-worker": "production SSR on workerd",
        "e2e": "playwright (chromium · firefox · webkit)",
        "e2e-live": "playwright (live API · chromium)",
        "images": "container images (build · smoke)",
        "lighthouse": "lighthouse budgets",
        "backend": "backend (ucgle_f1 tests + audits)",
        "backend-slow": "backend (slow audits)",
        "packages": "packages (qcompass-* + qfull-*)",
    }
    review = ci["jobs"]["dependency-review"]
    assert review["if"] == "github.event_name == 'pull_request'"
    assert review["permissions"] == {"contents": "read", "pull-requests": "write"}
    (action,) = [st for st in review["steps"] if "dependency-review-action" in str(st.get("uses"))]
    assert action["with"] == {
        "fail-on-severity": "high",
        "deny-licenses": (
            "GPL-1.0-or-later, GPL-2.0-only, GPL-2.0-or-later, GPL-3.0-only, GPL-3.0-or-later,"
            " AGPL-1.0-or-later, AGPL-3.0-only, AGPL-3.0-or-later, SSPL-1.0, BUSL-1.1,"
            " CC-BY-NC-4.0, EUPL-1.2"
        ),
        "comment-summary-in-pr": "on-failure",
    }
