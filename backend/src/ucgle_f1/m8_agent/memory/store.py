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
from typing import Any, Iterable, Literal, Optional, get_args

from sqlalchemy import Uuid, text
from sqlmodel import Field, Session, SQLModel, select

from ..._paths import safe_component, safe_join
from ...db import get_engine

# Approval scopes the tools check (``get_capabilities().approvalScopesRequired``).
# There is no wildcard: every token names its scopes and is spent once.
ApprovalScope = Literal[
    "start_run", "cancel_run", "scan_parameters", "save_plan", "precision_override",
]
APPROVAL_SCOPES: tuple[str, ...] = get_args(ApprovalScope)
# Longest approval lifetime, in seconds (round 2, c4).
APPROVAL_MAX_TTL_SECONDS = 3600

_REDACTED = "[redacted]"


# A key names a secret when, lower-cased and without '_', '-' and '.', it
# contains one of these: approval_token, approvalTokenId, tokenId, api_key,
# apiKey, client_secret, password ... (round 3B: round 2 matched only
# 'token' and '*_token', so RunConfig's agent.approvalTokenId was logged).
_SECRET_KEY_PARTS = ("token", "secret", "password", "apikey")


def redact_secrets(value: Any) -> Any:
    """Copy of ``value`` with the value of every secret-named key replaced.

    Tool-call logs (``agent_tool_calls``) are readable by every member of the
    tenant, viewers included; a token id is a bearer secret (round 2, c4).
    Keys are matched case-insensitively at any depth (``_SECRET_KEY_PARTS``).
    """
    if isinstance(value, dict):
        return {k: _REDACTED if _is_secret_key(k) and v is not None else redact_secrets(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_secrets(v) for v in value]
    return value


def _is_secret_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    folded = key.lower().replace("_", "").replace("-", "").replace(".", "")
    return any(part in folded for part in _SECRET_KEY_PARTS)


def validate_approval_request(scopes: Iterable[str], ttl_seconds: Any) -> tuple[str, ...]:
    """The scopes, sorted; ValueError unless they are known and 0 < ttl <= 3600."""
    wanted = tuple(sorted(set(scopes)))
    unknown = [sc for sc in wanted if sc not in APPROVAL_SCOPES]
    if not wanted or unknown:
        msg = f"scopes must be a non-empty subset of {list(APPROVAL_SCOPES)}; unknown: {unknown}"
        raise ValueError(msg)
    if (
        isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int)
        or not 0 < ttl_seconds <= APPROVAL_MAX_TTL_SECONDS
    ):
        msg = (
            f"ttl_seconds must be an integer in (0, {APPROVAL_MAX_TTL_SECONDS}]; "
            f"got {ttl_seconds!r}"
        )
        raise ValueError(msg)
    return wanted



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
        """Write the plan under ``agent-sandbox/<tenant id>/<conversation>/plans/``.

        The sandbox is keyed by the tenant's UUID, which never changes; a
        slug can be renamed and later taken by another tenant (round 3B).
        Both names must be single safe path components (``_paths``), so a
        plan never lands outside its tenant's sandbox. ``Plan.path`` is that
        location relative to the artifacts root, never a server path
        (round 2, c4; the same rule as SEC-L4's sidecar reference).
        """
        conversation = safe_component(conversation_id, "conversation id")
        tenant_uuid = self._tenant(tenant, create=True)
        if tenant_uuid is None:  # ensure_tenant always returns one
            msg = "save_plan needs a tenant"
            raise ValueError(msg)
        pid = f"plan_{secrets.token_hex(8)}"
        root = Path(os.environ.get(
            "UCGLE_F1_ARTIFACTS", str(Path.home() / ".ucgle_f1" / "artifacts"),
        ))
        path = safe_join(
            root, "agent-sandbox", safe_component(str(tenant_uuid), "tenant"), conversation,
            "plans", f"{pid}.json",
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
        row = Plan(
            planId=pid, conversationId=conversation_id,
            path=path.relative_to(os.path.realpath(root)).as_posix(), payload=json.dumps(payload),
            tenant_id=tenant_uuid,
        )
        with self._lock, Session(self._engine) as s:
            s.add(row)
            s.commit()
            s.refresh(row)
        return row

    # ── Approval tokens ────────────────────────────────────────────
    def issue_approval(
        self,
        scopes: Iterable[str],
        ttl_seconds: int = APPROVAL_MAX_TTL_SECONDS,
        *,
        tenant: str | None = None,
    ) -> ApprovalToken:
        """A one-shot token for ``scopes`` (from APPROVAL_SCOPES), valid for
        ``ttl_seconds`` (0 < ttl <= 3600); ValueError otherwise."""
        wanted = validate_approval_request(scopes, ttl_seconds)
        tok = ApprovalToken(
            tenant_id=self._tenant(tenant, create=True),
            tokenId=f"appr_{secrets.token_urlsafe(16)}",
            scopes=",".join(wanted),
            expiresAt=datetime.fromtimestamp(datetime.now(UTC).timestamp() + ttl_seconds, UTC),
        )
        with self._lock, Session(self._engine) as s:
            s.add(tok)
            s.commit()
            s.refresh(tok)
        return tok

    def approval_is_valid(self, token_id: str, required_scope: str, *, tenant: str | None = None) -> bool:
        """True iff ``consume_approval`` would spend ``token_id`` now; spends nothing.

        A cheap pre-check (one indexed SELECT) for a request that has costly
        validation to do before it spends its token (W1 R4-API: a scan with a
        bogus token is refused before any cell is validated). The spend
        itself is still ``consume_approval``'s conditional UPDATE.
        """
        if not token_id:
            return False
        owner = self._tenant(tenant, create=False)
        if owner is None:
            return False
        with self._engine.connect() as conn:
            found = conn.execute(
                text(
                    'select 1 from public.agent_approval_tokens '
                    'where "tokenId" = :t and tenant_id = cast(:tenant as uuid) and not consumed '
                    'and "expiresAt" > now() and :scope = any(string_to_array(scopes, \',\'))'
                ),
                {"t": token_id, "tenant": owner, "scope": required_scope},
            ).first()
        return found is not None

    def consume_approval(self, token_id: str, required_scope: str, *, tenant: str | None = None) -> bool:
        """Spend ``token_id``: True iff it is the tenant's, unspent, unexpired and
        carries ``required_scope``.

        One conditional UPDATE does the check and the spend, so concurrent
        requests on any number of API instances spend a token at most once
        (round 2, c4). Every token is one-shot; there is no wildcard scope.
        """
        if not token_id:
            return False
        owner = self._tenant(tenant, create=False)
        if owner is None:
            return False
        with self._engine.begin() as conn:
            spent = conn.execute(
                text(
                    'update public.agent_approval_tokens set consumed = true '
                    'where "tokenId" = :t and tenant_id = cast(:tenant as uuid) and not consumed '
                    'and "expiresAt" > now() and :scope = any(string_to_array(scopes, \',\')) '
                    'returning "tokenId"'
                ),
                {"t": token_id, "tenant": owner, "scope": required_scope},
            ).first()
        return spent is not None

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
        # Members read this log (20261031200400), so secrets never reach it.
        with self._lock, Session(self._engine) as s:
            s.add(ToolCallRecord(
                tenant_id=self._tenant(tenant, create=True),
                conversationId=conversation_id,
                tool=tool,
                requestJson=json.dumps(redact_secrets(request), default=str),
                responseJson=json.dumps(redact_secrets(response), default=str),
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
