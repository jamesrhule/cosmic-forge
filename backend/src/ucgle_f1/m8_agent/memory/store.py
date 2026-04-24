"""SQLite store for per-conversation state.

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
from typing import Iterable, Literal, Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

_DEFAULT_DB_PATH = Path(os.environ.get(
    "UCGLE_F1_STATE_DIR",
    str(Path.home() / ".ucgle_f1"),
)) / "agent.db"


# ── SQLModel tables ───────────────────────────────────────────────────


class Hypothesis(SQLModel, table=True):
    hypothesisId: str = Field(primary_key=True)
    conversationId: str = Field(index=True)
    text: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Plan(SQLModel, table=True):
    planId: str = Field(primary_key=True)
    conversationId: str = Field(index=True)
    path: str
    payload: str  # JSON
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalToken(SQLModel, table=True):
    tokenId: str = Field(primary_key=True)
    scopes: str  # comma-separated
    issuedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expiresAt: Optional[datetime] = None
    consumed: bool = False


class RunLink(SQLModel, table=True):
    runId: str = Field(primary_key=True)
    conversationId: str = Field(index=True)
    hypothesisId: str = Field(index=True)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolCallRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversationId: str = Field(index=True)
    tool: str
    requestJson: str
    responseJson: str
    ok: bool
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PatchRecord(SQLModel, table=True):
    patchId: str = Field(primary_key=True)
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
    """Thin façade over SQLModel tables with a module-wide engine."""

    db_path: Path = _DEFAULT_DB_PATH
    _lock: threading.RLock = threading.RLock()

    def __post_init__(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        SQLModel.metadata.create_all(self._engine)

    # ── Hypotheses ────────────────────────────────────────────────
    def record_hypothesis(self, conversation_id: str, text: str) -> Hypothesis:
        hid = f"hyp_{secrets.token_hex(8)}"
        row = Hypothesis(hypothesisId=hid, conversationId=conversation_id, text=text)
        with self._lock, Session(self._engine) as s:
            s.add(row)
            s.commit()
            s.refresh(row)
        return row

    def get_hypothesis(self, hypothesis_id: str) -> Hypothesis | None:
        with Session(self._engine) as s:
            return s.get(Hypothesis, hypothesis_id)

    # ── Plans ──────────────────────────────────────────────────────
    def save_plan(self, conversation_id: str, payload: dict) -> Plan:
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
        )
        with self._lock, Session(self._engine) as s:
            s.add(row)
            s.commit()
            s.refresh(row)
        return row

    # ── Approval tokens ────────────────────────────────────────────
    def issue_approval(self, scopes: Iterable[str], ttl_seconds: int | None = 3600) -> ApprovalToken:
        tok = ApprovalToken(
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

    def consume_approval(self, token_id: str, required_scope: str) -> bool:
        """Return True iff ``token_id`` carries ``required_scope`` and is fresh."""
        if not token_id:
            return False
        with self._lock, Session(self._engine) as s:
            tok = s.get(ApprovalToken, token_id)
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
    def link_run(self, run_id: str, conversation_id: str, hypothesis_id: str) -> None:
        with self._lock, Session(self._engine) as s:
            s.merge(RunLink(
                runId=run_id,
                conversationId=conversation_id,
                hypothesisId=hypothesis_id,
            ))
            s.commit()

    def run_link(self, run_id: str) -> RunLink | None:
        with Session(self._engine) as s:
            return s.get(RunLink, run_id)

    # ── Tool-call audit ────────────────────────────────────────────
    def record_tool_call(
        self,
        conversation_id: str,
        tool: str,
        request: dict,
        response: dict,
        ok: bool,
    ) -> None:
        with self._lock, Session(self._engine) as s:
            s.add(ToolCallRecord(
                conversationId=conversation_id,
                tool=tool,
                requestJson=json.dumps(request, default=str),
                responseJson=json.dumps(response, default=str),
                ok=ok,
            ))
            s.commit()

    def tool_calls(self, conversation_id: str) -> list[ToolCallRecord]:
        with Session(self._engine) as s:
            return list(s.exec(
                select(ToolCallRecord).where(
                    ToolCallRecord.conversationId == conversation_id,
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
    ) -> None:
        with self._lock, Session(self._engine) as s:
            s.add(PatchRecord(
                patchId=patch_id,
                conversationId=conversation_id,
                targetPath=target_path,
                rationale=rationale,
                unifiedDiff=unified_diff,
            ))
            s.commit()

    def get_patch(self, patch_id: str) -> PatchRecord | None:
        with Session(self._engine) as s:
            return s.get(PatchRecord, patch_id)

    def update_patch_status(
        self, patch_id: str, status: Literal["draft", "open", "approved", "rejected"],
    ) -> None:
        with self._lock, Session(self._engine) as s:
            row = s.get(PatchRecord, patch_id)
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
