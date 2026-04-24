"""Patch tools.

The agent can propose, dry-run, and request review of code patches
against ANY file in the repo — but it can NEVER apply them. Patches
reach the main branch only through an external human-driven Git
workflow (Claude Code wires the GitHub PR webhook separately).

Each dry-run runs in an ephemeral Docker container when possible.
When Docker is unavailable (CI, sandbox) we fall back to a
subprocess sandbox that reuses the current virtualenv but writes
into a temporary worktree. Egress is blocked at the Docker network
level (``network_mode='none'``); the subprocess fallback unsets
HTTP(S) proxy env vars and removes /etc/resolv.conf from the
container entrypoint only — the subprocess mode documents that
hosts may have egress and flags A3 violations accordingly.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from pydantic import BaseModel

from ...domain import (
    PatchProposal,
    PatchTestReport,
    ReviewTicket,
    ServiceError,
    ToolSpec,
)
from ..memory import get_store
from ..sandbox.dry_run import dry_run_patch as _dry_run_impl


class ProposePatchInput(BaseModel):
    conversation_id: str
    target_path: str
    rationale: str
    unified_diff: str


class DryRunInput(BaseModel):
    patch_id: str
    in_docker: bool = True


class RequestReviewInput(BaseModel):
    patch_id: str


def propose_patch(
    conversation_id: str,
    target_path: str,
    rationale: str,
    unified_diff: str,
) -> PatchProposal:
    if not unified_diff.strip():
        raise ServiceError("INVALID_INPUT", "unified_diff is empty")
    pid = f"patch_{secrets.token_hex(8)}"
    get_store().record_patch(
        conversation_id=conversation_id,
        patch_id=pid,
        target_path=target_path,
        rationale=rationale,
        unified_diff=unified_diff,
    )
    return PatchProposal(
        patchId=pid,
        targetPath=target_path,
        rationale=rationale,
        unifiedDiff=unified_diff,
        createdAt=datetime.now(UTC),
    )


def dry_run_patch(patch_id: str, in_docker: bool = True) -> PatchTestReport:
    row = get_store().get_patch(patch_id)
    if row is None:
        raise ServiceError("NOT_FOUND", f"patch {patch_id} not found")
    return _dry_run_impl(
        patch_id=patch_id,
        target_path=row.targetPath,
        unified_diff=row.unifiedDiff,
        in_docker=in_docker,
    )


def request_human_review(patch_id: str) -> ReviewTicket:
    row = get_store().get_patch(patch_id)
    if row is None:
        raise ServiceError("NOT_FOUND", f"patch {patch_id} not found")
    get_store().update_patch_status(patch_id, "open")
    return ReviewTicket(
        patchId=patch_id,
        ticketId=f"review_{patch_id}",
        createdAt=datetime.now(UTC),
        status="open",
    )


def _schema(m: type[BaseModel]) -> dict:
    return m.model_json_schema()


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="propose_patch", family="patch",
        description="Register a unified-diff patch proposal. No write effect.",
        approvalRequired=False,
        inputSchema=_schema(ProposePatchInput),
        outputSchema=_schema(PatchProposal),
    ),
    ToolSpec(
        name="dry_run_patch", family="patch",
        description="Run affected tests + S1–S15 subset in an ephemeral sandbox.",
        approvalRequired=False,
        inputSchema=_schema(DryRunInput),
        outputSchema=_schema(PatchTestReport),
    ),
    ToolSpec(
        name="request_human_review", family="patch",
        description="Mark a patch as ready for human review (open PR).",
        approvalRequired=False,
        inputSchema=_schema(RequestReviewInput),
        outputSchema=_schema(ReviewTicket),
    ),
]
