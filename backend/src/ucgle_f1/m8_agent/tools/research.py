"""Research tools: hypothesis/plan management + literature lookups.

Write scope: artifacts/agent-sandbox/{conversation_id}/. The
filesystem paths resolve via UCGLE_F1_ARTIFACTS (default
~/.ucgle_f1/artifacts).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ...domain import (
    AuditCheckId,
    AuditExplanation,
    CitationRecord,
    ExperimentPlan,
    HypothesisRef,
    LiteratureSummary,
    PlanRef,
    RunConfig,
    ScanSpec,
    ServiceError,
    ToolSpec,
)
from ..memory import get_store
from ..runs import get_registry

_BIB_PATH = Path(__file__).resolve().parents[1] / "bibliography.json"


def _bib() -> dict[str, Any]:
    return json.loads(_BIB_PATH.read_text())


class ProposeExperimentsInput(BaseModel):
    hypothesis: str
    constraints: dict[str, Any] | None = None
    budget: dict[str, Any] | None = None


class RecordHypothesisInput(BaseModel):
    conversation_id: str
    text: str


class SavePlanInput(BaseModel):
    plan: ExperimentPlan
    approval_token: str
    conversation_id: str


class ExplainAuditInput(BaseModel):
    run_id: str
    check_id: AuditCheckId


class SummarizeLiteratureInput(BaseModel):
    topic: str
    k: int = 5


def propose_experiments(
    hypothesis: str,
    constraints: dict[str, Any] | None = None,
    budget: dict[str, Any] | None = None,
) -> ExperimentPlan:
    _ = constraints, budget
    # Heuristic plan scaffold — the agent fills in the bodies.
    steps = [
        "scan couplings.xi over [1e-4, 1e-2] at fixed θ_grav",
        "cross-check F_GB stability with precision='high'",
        "compare η_B against V2 (Kawai-Kim) at matched T_reh",
        "check S10 ghost bound along the scan diagonal",
        "integrate ΔQ_A from Ω_gw^±(q,τ) for the V4 cross-check",
    ]
    citations = [b["arxivId"] for b in _bib()["benchmarks"]]
    return ExperimentPlan(
        hypothesis=hypothesis,
        steps=steps,
        suggestedConfigs=[],  # agent fills in
        citations=citations,
    )


def record_hypothesis(conversation_id: str, text: str) -> HypothesisRef:
    row = get_store().record_hypothesis(conversation_id=conversation_id, text=text)
    return HypothesisRef(
        conversationId=row.conversationId,
        hypothesisId=row.hypothesisId,
        text=row.text,
        createdAt=row.createdAt,
    )


def save_plan(
    plan: ExperimentPlan,
    approval_token: str,
    conversation_id: str,
) -> PlanRef:
    if not get_store().consume_approval(approval_token, "save_plan"):
        raise ServiceError("APPROVAL_REQUIRED",
                           "approval required for save_plan (scope 'save_plan')")
    row = get_store().save_plan(conversation_id, plan.model_dump())
    return PlanRef(
        conversationId=row.conversationId,
        planId=row.planId,
        path=row.path,
    )


def cite_paper(arxiv_id: str) -> CitationRecord:
    for b in _bib()["benchmarks"]:
        if b["arxivId"] == arxiv_id:
            return CitationRecord(
                arxivId=b["arxivId"],
                title=b["title"],
                authors=b["authors"],
                year=b["year"],
                references=[b["id"]],
            )
    raise ServiceError("NOT_FOUND", f"arXiv:{arxiv_id} is not in the shipped bibliography")


def explain_audit(run_id: str, check_id: AuditCheckId) -> AuditExplanation:
    r = get_registry().result(run_id)
    if r is None:
        raise ServiceError("NOT_FOUND", f"run {run_id} not found")
    check = next((c for c in r.audit.checks if c.id == check_id), None)
    if check is None:
        raise ServiceError("NOT_FOUND", f"{check_id} not in run {run_id} audit")
    return AuditExplanation(
        runId=run_id,
        checkId=check_id,
        verdict=check.verdict,
        reasoning=(
            f"Check {check_id} ({check.name}) returned {check.verdict}"
            + (f" with value={check.value}" if check.value is not None else "")
            + (f" against tolerance={check.tolerance}" if check.tolerance is not None else "")
        ),
        references=check.references,
    )


def summarize_literature(topic: str, k: int = 5) -> LiteratureSummary:
    bib = _bib()["benchmarks"]
    entries = [
        CitationRecord(
            arxivId=b["arxivId"],
            title=b["title"],
            authors=b["authors"],
            year=b["year"],
            references=[b["id"]],
        )
        for b in bib[:k]
    ]
    summary = (
        f"{len(entries)} references covering {topic}. "
        "Primary benchmark V2 (Kawai-Kim 1702.07689) sets the η_B target."
    )
    return LiteratureSummary(topic=topic, entries=entries, summary=summary)


def suggest_next_parameter_scan(run_id: str) -> ScanSpec:
    r = get_registry().result(run_id)
    if r is None:
        raise ServiceError("NOT_FOUND", f"run {run_id} not found")
    # Heuristic: scan xi and theta_grav around the current values.
    base: RunConfig = r.config
    xi0 = float(base.couplings.xi) or 1.0e-3
    theta0 = float(base.couplings.theta_grav) or 1.0e-3
    from ...domain import ScanAxis

    return ScanSpec(
        base=base,
        axes=[
            ScanAxis(name="xi", path="couplings.xi",
                     min=xi0 * 0.3, max=xi0 * 3.0, points=9, log=True),
            ScanAxis(name="theta_grav", path="couplings.theta_grav",
                     min=theta0 * 0.3, max=theta0 * 3.0, points=9, log=True),
        ],
    )


def _schema(m: type[BaseModel]) -> dict:
    return m.model_json_schema()


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="propose_experiments", family="research",
        description="Draft an ExperimentPlan from a hypothesis + constraints.",
        approvalRequired=False,
        inputSchema=_schema(ProposeExperimentsInput),
        outputSchema=_schema(ExperimentPlan),
    ),
    ToolSpec(
        name="record_hypothesis", family="research",
        description="Persist a hypothesis keyed by conversation_id.",
        approvalRequired=False,
        inputSchema=_schema(RecordHypothesisInput),
        outputSchema=_schema(HypothesisRef),
    ),
    ToolSpec(
        name="save_plan", family="research",
        description="Serialize a plan to the sandbox. Approval scope: 'save_plan'.",
        approvalRequired=True,
        inputSchema=_schema(SavePlanInput),
        outputSchema=_schema(PlanRef),
    ),
    ToolSpec(
        name="cite_paper", family="research",
        description="Resolve an arXiv ID against the shipped bibliography.",
        approvalRequired=False,
        inputSchema={"properties": {"arxiv_id": {"type": "string"}},
                     "required": ["arxiv_id"]},
        outputSchema=_schema(CitationRecord),
    ),
    ToolSpec(
        name="explain_audit", family="research",
        description="Explain one S1–S15 verdict for a given run.",
        approvalRequired=False,
        inputSchema=_schema(ExplainAuditInput),
        outputSchema=_schema(AuditExplanation),
    ),
    ToolSpec(
        name="summarize_literature", family="research",
        description="Return the top-k citation entries for a topic.",
        approvalRequired=False,
        inputSchema=_schema(SummarizeLiteratureInput),
        outputSchema=_schema(LiteratureSummary),
    ),
    ToolSpec(
        name="suggest_next_parameter_scan", family="research",
        description="Propose a follow-up ScanSpec anchored on a completed run.",
        approvalRequired=False,
        inputSchema={"properties": {"run_id": {"type": "string"}},
                     "required": ["run_id"]},
        outputSchema=_schema(ScanSpec),
    ),
]
