"""Postgres store for per-conversation agent state (P3-01; was SQLite).

Persists:
  • hypotheses (A6 traceability)
  • plans       (sandbox-only write scope)
  • approval tokens + their scope
  • run ↔ conversation mapping
  • tool-call audit log (A1, A4)
"""

from __future__ import annotations

import json
import os
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

from sqlalchemy import Uuid
from sqlmodel import Field, Session, SQLModel, select

from ...db import get_engine



# ── SQLModel tables ───────────────────────────────────────────────────


class Hypothesis(SQLModel, table=True):
    __tablename__ = "agent_hypotheses"  # supabase/migrations/20261031160000_*

    hypothesisId: str = Field(primary_key=True)
    # SF4: owning tenant (20261031200400); every read and write filters on it.
    tenant_id: Optional[str] = Field(default=None, sa_type=Uuid(as_uuid=False))
    conversationId: str = Field(index=True)
    text: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Plan(SQLModel, table=True):
    __tablename__ = "agent_plans"  # supabase/migrations/20261031160000_*

    planId: str = Field(primary_key=True)
    # SF4: owning tenant (20261031200400); every read and write filters on it.
    tenant_id: Optional[str] = Field(default=None, sa_type=Uuid(as_uuid=False))
    conversationId: str = Field(index=True)
    path: str
    payload: str  # JSON
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalToken(SQLModel, table=True):
    __tablename__ = "agent_approval_tokens"  # supabase/migrations/20261031160000_*

    tokenId: str = Field(primary_key=True)
    # SF4: owning tenant (20261031200400); every read and write filters on it.
    tenant_id: Optional[str] = Field(default=None, sa_type=Uuid(as_uuid=False))
    scopes: str  # comma-separated
    issuedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expiresAt: Optional[datetime] = None
    consumed: bool = False


class RunLink(SQLModel, table=True):
    __tablename__ = "agent_run_links"  # supabase/migrations/20261031160000_*

    runId: str = Field(primary_key=True)
    # SF4: owning tenant (20261031200400); every read and write filters on it.
    tenant_id: Optional[str] = Field(default=None, sa_type=Uuid(as_uuid=False))
    conversationId: str = Field(index=True)
    hypothesisId: str = Field(index=True)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolCallRecord(SQLModel, table=True):
    __tablename__ = "agent_tool_calls"  # supabase/migrations/20261031160000_*

    id: Optional[int] = Field(default=None, primary_key=True)
    # SF4: owning tenant (20261031200400); every read and write filters on it.
    tenant_id: Optional[str] = Field(default=None, sa_type=Uuid(as_uuid=False))
    conversationId: str = Field(index=True)
    tool: str
    requestJson: str
    responseJson: str
    ok: bool
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PatchRecord(SQLModel, table=True):
    __tablename__ = "agent_patches"  # supabase/migrations/20261031160000_*

    patchId: str = Field(primary_key=True)
    # SF4: owning tenant (20261031200400); every read and write filters on it.
    tenant_id: Optional[str] = Field(default=None, sa_type=Uuid(as_uuid=False))
    conversationId: str = Field(index=True)
    targetPath: str
    rationale: str
    unifiedDiff: str
    # SQLModel cannot map a Literal type directly to a column; we
    # enforce the enumeration at the API boundary instead.
    reviewStatus: str = "draft"
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ConversationStore:
    """Thin façade over the ``agent_*`` tables on the shared Postgres engine.

    The schema is owned by ``supabase/migrations`` (no ``create_all``).
    """

    _lock: threading.RLock = threading.RLock()

    def __post_init__(self) -> None:
        self._engine = get_engine()

    def ping(self) -> None:
        """Raise if the backing database is unreachable (``/readyz``)."""
        from sqlalchemy import text

        with Session(self._engine) as s:
            s.exec(text("SELECT 1"))  # type: ignore[call-overload]

    # ── Tenancy (SF4) ─────────────────────────────────────────────
    # Every method takes ``tenant`` (the principal's tenant slug or UUID).
    # ``None`` means the bound tenant, or the dev tenant under
    # QCOMPASS_ENV=dev only (``principal.resolve_tenant_slug``). Rows of
    # another tenant are invisible: reads return None / [] and approvals
    # don't verify.
    @staticmethod
    def _tenant(tenant: str | None, *, create: bool) -> str | None:
        from ..auth import get_auth_store
        from ..principal import resolve_tenant_slug

        slug = resolve_tenant_slug(tenant)
        store = get_auth_store()
        if create:
            return store.ensure_tenant(slug)
        found = store.resolve_tenant(slug)
        return found[0] if found else None

    @classmethod
    def _owned(cls, row: Any, tenant: str | None) -> Any:
        if row is None:
            return None
        owner = cls._tenant(tenant, create=False)
        return row if owner is not None and str(row.tenant_id) == owner else None

    # ── Hypotheses ────────────────────────────────────────────────
    def record_hypothesis(self, conversation_id: str, text: str, *, tenant: str | None = None) -> Hypothesis:
        hid = f"hyp_{secrets.token_hex(8)}"
        row = Hypothesis(
            hypothesisId=hid, conversationId=conversation_id, text=text,
            tenant_id=self._tenant(tenant, create=True),
        )
        with self._lock, Session(self._engine) as s:
            s.add(row)
            s.commit()
            s.refresh(row)
        return row

    def get_hypothesis(self, hypothesis_id: str, *, tenant: str | None = None) -> Hypothesis | None:
        with Session(self._engine) as s:
            return self._owned(s.get(Hypothesis, hypothesis_id), tenant)

    # ── Plans ──────────────────────────────────────────────────────
    def save_plan(self, conversation_id: str, payload: dict, *, tenant: str | None = None) -> Plan:
        pid = f"plan_{secrets.token_hex(8)}"
        root = Path(os.environ.get(
            "UCGLE_F1_ARTIFACTS", str(Path.home() / ".ucgle_f1" / "artifacts"),
        ))
        path = root / "agent-sandbox" / conversation_id / "plans" / f"{pid}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
        row = Plan(
            planId=pid, conversationId=conversation_id,
            path=str(path), payload=json.dumps(payload),
            tenant_id=self._tenant(tenant, create=True),
        )
        with self._lock, Session(self._engine) as s:
            s.add(row)
            s.commit()
            s.refresh(row)
        return row

    # ── Approval tokens ────────────────────────────────────────────
    def issue_approval(
        self, scopes: Iterable[str], ttl_seconds: int | None = 3600, *, tenant: str | None = None,
    ) -> ApprovalToken:
        tok = ApprovalToken(
            tenant_id=self._tenant(tenant, create=True),
            tokenId=f"appr_{secrets.token_urlsafe(16)}",
            scopes=",".join(sorted(set(scopes))),
            expiresAt=(
                datetime.now(UTC).replace(microsecond=0)
                if ttl_seconds is None
                else datetime.fromtimestamp(
                    datetime.now(UTC).timestamp() + ttl_seconds, UTC
                )
            ),
        )
        with self._lock, Session(self._engine) as s:
            s.add(tok)
            s.commit()
            s.refresh(tok)
        return tok

    def consume_approval(self, token_id: str, required_scope: str, *, tenant: str | None = None) -> bool:
        """Return True iff ``token_id`` is the tenant's, carries ``required_scope`` and is fresh."""
        if not token_id:
            return False
        with self._lock, Session(self._engine) as s:
            tok = self._owned(s.get(ApprovalToken, token_id), tenant)
            if tok is None or tok.consumed:
                return False
            scopes = set(tok.scopes.split(","))
            if required_scope not in scopes and "*" not in scopes:
                return False
            # SQLite strips tz info on round-trip, so re-anchor to UTC
            # before comparing with ``datetime.now(UTC)``.
            if tok.expiresAt is not None:
                exp = tok.expiresAt
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=UTC)
                if exp < datetime.now(UTC):
                    return False
            # One-shot tokens: mark consumed. Session-wide tokens use scope '*'.
            if "*" not in scopes:
                tok.consumed = True
                s.add(tok)
                s.commit()
            return True

    # ── Run linking (A6) ───────────────────────────────────────────
    def link_run(
        self, run_id: str, conversation_id: str, hypothesis_id: str, *, tenant: str | None = None,
    ) -> None:
        with self._lock, Session(self._engine) as s:
            s.merge(RunLink(
                runId=run_id,
                conversationId=conversation_id,
                hypothesisId=hypothesis_id,
                tenant_id=self._tenant(tenant, create=True),
            ))
            s.commit()

    def run_link(self, run_id: str, *, tenant: str | None = None) -> RunLink | None:
        with Session(self._engine) as s:
            return self._owned(s.get(RunLink, run_id), tenant)

    # ── Tool-call audit ────────────────────────────────────────────
    def record_tool_call(
        self,
        conversation_id: str,
        tool: str,
        request: dict,
        response: dict,
        ok: bool,
        *,
        tenant: str | None = None,
    ) -> None:
        with self._lock, Session(self._engine) as s:
            s.add(ToolCallRecord(
                tenant_id=self._tenant(tenant, create=True),
                conversationId=conversation_id,
                tool=tool,
                requestJson=json.dumps(request, default=str),
                responseJson=json.dumps(response, default=str),
                ok=ok,
            ))
            s.commit()

    def tool_calls(self, conversation_id: str, *, tenant: str | None = None) -> list[ToolCallRecord]:
        owner = self._tenant(tenant, create=False)
        if owner is None:
            return []
        with Session(self._engine) as s:
            return list(s.exec(
                select(ToolCallRecord).where(
                    ToolCallRecord.conversationId == conversation_id,
                    ToolCallRecord.tenant_id == owner,
                ).order_by(ToolCallRecord.id)
            ))

    # ── Patch records ──────────────────────────────────────────────
    def record_patch(
        self,
        conversation_id: str,
        patch_id: str,
        target_path: str,
        rationale: str,
        unified_diff: str,
        *,
        tenant: str | None = None,
    ) -> None:
        with self._lock, Session(self._engine) as s:
            s.add(PatchRecord(
                tenant_id=self._tenant(tenant, create=True),
                patchId=patch_id,
                conversationId=conversation_id,
                targetPath=target_path,
                rationale=rationale,
                unifiedDiff=unified_diff,
            ))
            s.commit()

    def get_patch(self, patch_id: str, *, tenant: str | None = None) -> PatchRecord | None:
        with Session(self._engine) as s:
            return self._owned(s.get(PatchRecord, patch_id), tenant)

    def update_patch_status(
        self, patch_id: str, status: Literal["draft", "open", "approved", "rejected"],
        *, tenant: str | None = None,
    ) -> None:
        with self._lock, Session(self._engine) as s:
            row = self._owned(s.get(PatchRecord, patch_id), tenant)
            if row is None:
                return
            row.reviewStatus = status
            s.add(row)
            s.commit()


_store_singleton: ConversationStore | None = None


def get_store() -> ConversationStore:
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = ConversationStore()
    return _store_singleton


def reset_store() -> None:
    """Drop the singleton (tests that switch ``DATABASE_URL``)."""
    global _store_singleton
    _store_singleton = None
