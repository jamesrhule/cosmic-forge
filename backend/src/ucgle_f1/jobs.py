"""Job queue and run records on main's Supabase schema (P3-02, P3-03).

The only queue is ``public.jobs`` with main's ``claim_next_job`` /
``complete_job`` (Part 4, R20), plus ``heartbeat_job`` and
``reap_expired_jobs`` from ``20261031180000_qcompass_worker_queue.sql``.
Those functions are service-role only; the API and workers connect with a
privileged ``DATABASE_URL`` and identify as ``service_role`` per transaction
(``request.jwt.claims``), exactly as PostgREST does for the service key.

Run records live in ``public.runs`` (one row per run, tenant-scoped through
``tenant_id``), full results in ``public.run_results`` (P3-03) and progress
events in ``public.job_events`` (written by workers as each module finishes,
read by the SSE/WebSocket streams).
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, Engine, text

from .db import get_engine

JOB_KINDS = (
    "ucgle_f1.run",
    "qcompass.run",
    "scan",
    "viz.bake",
    "qpu.submit",
    "qpu.poll",
    "patch.dryrun",
)
COMPUTE_CLASSES = ("cpu", "gpu_small", "gpu_large", "qpu", "edge")
TERMINAL_RUN_STATUSES = frozenset({"completed", "failed", "canceled"})

_SERVICE_CLAIMS = json.dumps({"role": "service_role"})


def _finite(obj: Any) -> Any:
    """JSON-safe copy: Postgres ``jsonb`` has no NaN/Infinity, so non-finite
    floats are stored as the strings ``"NaN"``, ``"Infinity"``, ``"-Infinity"``
    (pydantic reads them back as floats)."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return "NaN" if math.isnan(obj) else ("Infinity" if obj > 0 else "-Infinity")
    if isinstance(obj, dict):
        return {k: _finite(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_finite(v) for v in obj]
    return obj


def _dumps(obj: Any) -> str:
    return json.dumps(_finite(obj), default=str, allow_nan=False)


def _as_service(conn: Connection) -> None:
    conn.execute(
        text("select set_config('request.jwt.claims', :c, true)"), {"c": _SERVICE_CLAIMS},
    )


@dataclass(frozen=True)
class Job:
    id: str
    tenant_id: str
    run_id: str | None
    kind: str
    payload: dict[str, Any]
    compute_class: str
    attempts: int
    max_attempts: int


@dataclass(frozen=True)
class RunRecord:
    id: str
    tenant_id: str
    status: str
    label: str
    config: dict[str, Any]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    # The client's runId, a per-tenant alias of ``id`` (round 2, c4/SEC-L2).
    client_run_id: str | None = None


@dataclass(frozen=True)
class JobEvent:
    id: int
    run_id: str
    type: str
    payload: dict[str, Any]
    created_at: datetime


class JobQueue:
    """Enqueue, lease, heartbeat, complete and reap jobs; record run events."""

    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    @property
    def engine(self) -> Engine:
        return self._engine

    def ping(self) -> None:
        with self._engine.connect() as conn:
            conn.execute(text("select 1 from public.jobs limit 1"))

    # ── runs ──────────────────────────────────────────────────────────

    def enqueue_run(
        self,
        *,
        run_id: str,
        tenant_uuid: str,
        kind: str,
        payload: dict[str, Any],
        label: str,
        config: dict[str, Any],
        compute_class: str = "cpu",
        max_attempts: int = 3,
        created_by: str | None = None,
        enforce_limits: bool = True,
        client_run_id: str | None = None,
    ) -> str:
        """Check the tenant's plan limits (P3-05), then insert the run row and
        its job atomically; return the job id.

        ``run_id`` is the server-generated primary key; ``client_run_id`` is
        the caller's own name for the run, unique within its tenant.
        """
        if kind not in JOB_KINDS:
            raise ValueError(f"unknown job kind {kind!r}")
        if compute_class not in COMPUTE_CLASSES:
            raise ValueError(f"unknown compute class {compute_class!r}")
        from .plans import enforce_at_enqueue

        with self._engine.begin() as conn:
            if enforce_limits:
                enforce_at_enqueue(
                    conn, tenant_uuid, compute_class,
                    timeline_bytes=payload.get("timeline_bytes") if kind == "viz.bake" else None,
                )
            conn.execute(
                text(
                    "insert into public.runs (id, tenant_id, visibility, status, label, config, precision, "
                    "client_run_id) values (:id, cast(:tenant as uuid), 'private', 'queued', :label, "
                    "cast(:config as jsonb), :precision, :alias)"
                ),
                {
                    "id": run_id, "tenant": tenant_uuid, "label": label, "alias": client_run_id,
                    "config": _dumps(config),
                    "precision": config.get("precision") if isinstance(config.get("precision"), str) else None,
                },
            )
            job_id = conn.execute(
                text(
                    "insert into public.jobs (tenant_id, run_id, kind, payload, compute_class, "
                    "max_attempts, created_by) values (cast(:tenant as uuid), :run, :kind, "
                    "cast(:payload as jsonb), cast(:cls as public.compute_class), :max, "
                    "cast(:by as uuid)) returning id::text"
                ),
                {
                    "tenant": tenant_uuid, "run": run_id, "kind": kind,
                    "payload": _dumps(payload), "cls": compute_class,
                    "max": max_attempts, "by": created_by,
                },
            ).scalar_one()
            self._emit(conn, job_id, run_id, tenant_uuid, "status", _status("queued"))
        return str(job_id)

    # A tenant's runs are the ones the API created for it. A client can write
    # rows into public.runs through PostgREST (main's personal-run
    # persistence); those always carry their author and are never served
    # as the tenant's platform runs (round 2, c2).
    _API_RUN = "author_user_id is null"
    _RUN_COLUMNS = (
        "id, tenant_id::text as tenant_id, status::text as status, coalesce(label, '') as label, "
        "config, created_at, started_at, completed_at, client_run_id"
    )

    def get_run(self, run_id: str, *, tenant_uuid: str | None = None) -> RunRecord | None:
        """The run ``run_id``; with a tenant, that tenant's API run whose id or
        client alias is ``run_id`` (the id wins)."""
        sql = f"select {self._RUN_COLUMNS} from public.runs where id = :id"
        params: dict[str, Any] = {"id": run_id}
        if tenant_uuid is not None:
            sql = (
                f"select {self._RUN_COLUMNS} from public.runs "
                f"where (id = :id or client_run_id = :id) and tenant_id = cast(:tenant as uuid) "
                f"and {self._API_RUN} order by (id = :id) desc limit 1"
            )
            params["tenant"] = tenant_uuid
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        return _run(row) if row else None

    def list_runs(
        self, *, tenant_uuid: str, domain: str | None = None, limit: int = 100, offset: int = 0,
    ) -> list[RunRecord]:
        sql = (
            f"select {self._RUN_COLUMNS} from public.runs "
            f"where tenant_id = cast(:tenant as uuid) and {self._API_RUN}"
        )
        params: dict[str, Any] = {"tenant": tenant_uuid, "limit": limit, "offset": offset}
        if domain is not None:
            sql += " and config ->> 'domain' = :domain"
            params["domain"] = domain
        sql += " order by created_at desc, id desc limit :limit offset :offset"
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [_run(r) for r in rows]

    # SF2: a worker's writes to a run carry its lease — job, worker id and
    # attempt (jobs.attempts as the claim returned it) — and land only while
    # that attempt holds the job (status 'running') and the job is this
    # run's. An abandoned attempt, or a stale worker reusing the worker id,
    # no longer matches once the job is claimed again. The job row is
    # locked FOR SHARE until the write commits, so a cancel or completion
    # (which lock it FOR UPDATE) is ordered before or after the write,
    # never between the check and the write; every path takes the job row
    # before the run row (lock order, see cancel_run).
    _LEASE = (
        "exists (select 1 from public.jobs lj where lj.id = cast(:lease_job as uuid) "
        "and lj.run_id = :lease_run and lj.locked_by = :lease_worker "
        "and lj.attempts = :lease_attempt and lj.status = 'running' for share)"
    )

    @classmethod
    def _lease_clause(
        cls, run_id: str, job_id: str | None, worker_id: str | None, attempt: int | None,
    ) -> tuple[str, dict[str, Any]]:
        if job_id is None and worker_id is None and attempt is None:
            return "", {}
        if job_id is None or worker_id is None or attempt is None:
            raise ValueError("a lease is job_id, worker_id and attempt together; pass all three or none")
        return f" and {cls._LEASE}", {
            "lease_job": job_id, "lease_run": run_id, "lease_worker": worker_id, "lease_attempt": int(attempt),
        }

    # Sticky run states: queued -> running -> terminal (a run may also fail
    # or be canceled before it starts); a terminal run never changes again.
    # The trigger runs_status_transition (20261102105000) enforces the same
    # rule for every writer; this predicate makes a refused write return
    # False instead of raising.
    _FROM = (
        "((:s = 'running' and status in ('queued', 'running')) "
        "or (:s in ('failed', 'canceled') and status in ('queued', 'running')) "
        "or (:s = 'completed' and status = 'running'))"
    )

    def set_run_status(
        self, run_id: str, status: str, *, job_id: str | None = None, worker_id: str | None = None,
        attempt: int | None = None,
    ) -> bool:
        """Set the run's status; False when nothing changed (lease lost, or the run already ended)."""
        lease, params = self._lease_clause(run_id, job_id, worker_id, attempt)
        with self._engine.begin() as conn:
            res = conn.execute(
                text(
                    "update public.runs set status = cast(:s as public.run_status), "
                    "started_at = case when :s = 'running' then coalesce(started_at, now()) else started_at end, "
                    "completed_at = case when :s in ('completed', 'failed', 'canceled') then now() "
                    f"else completed_at end, updated_at = now() where id = :id and {self._FROM}"
                    + lease
                ),
                {"s": status, "id": run_id, **params},
            )
        return res.rowcount > 0

    def save_result(
        self, run_id: str, payload: dict[str, Any], *, job_id: str | None = None, worker_id: str | None = None,
        attempt: int | None = None,
    ) -> bool:
        """Store the full result payload (P3-03); returned verbatim by the API.

        False when nothing was stored (lease lost, or the run already ended:
        a terminal run's result never changes).
        """
        lease, params = self._lease_clause(run_id, job_id, worker_id, attempt)
        with self._engine.begin() as conn:
            res = conn.execute(
                text(
                    "insert into public.run_results (run_id, payload) "
                    "select cast(:id as text), cast(:p as jsonb) where exists "
                    "(select 1 from public.runs r where r.id = :id and r.status in ('queued', 'running'))"
                    + lease
                    + " on conflict (run_id) do update set payload = excluded.payload, updated_at = now()"
                ),
                {"id": run_id, "p": _dumps(payload), **params},
            )
        return res.rowcount > 0

    @staticmethod
    def _result_sql(column: str, tenant_uuid: str | None) -> tuple[str, dict[str, Any]]:
        # SEC-H2: with a tenant, the result is returned only when the run
        # itself belongs to that tenant.
        if tenant_uuid is None:
            return f"select {column} from public.run_results where run_id = :id", {}
        return (
            f"select rr.{column} from public.run_results rr join public.runs r on r.id = rr.run_id "
            "where rr.run_id = :id and r.tenant_id = cast(:tenant as uuid) and r.author_user_id is null",
            {"tenant": tenant_uuid},
        )

    def result(self, run_id: str, *, tenant_uuid: str | None = None) -> dict[str, Any] | None:
        sql, params = self._result_sql("payload", tenant_uuid)
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"id": run_id, **params}).first()
        return dict(row[0]) if row else None

    def result_text(self, run_id: str, *, tenant_uuid: str | None = None) -> str | None:
        """The stored payload as Postgres serialises it (stable across restarts)."""
        sql, params = self._result_sql("payload::text", tenant_uuid)
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"id": run_id, **params}).first()
        return str(row[0]) if row else None

    def ended(self, run_id: str, *, tenant_uuid: str, grace_seconds: float) -> tuple[str, datetime] | None:
        """(status, ended at) of a run that has been terminal for at least
        ``grace_seconds`` (by the database clock), else None (SF1: streams of
        a run that ended without a terminal event)."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "select status::text, coalesce(completed_at, updated_at) from public.runs "
                    "where id = :id and tenant_id = cast(:tenant as uuid) "
                    "and status in ('completed', 'failed', 'canceled') "
                    "and coalesce(completed_at, updated_at) <= now() - make_interval(secs => :grace)"
                ),
                {"id": run_id, "tenant": tenant_uuid, "grace": float(grace_seconds)},
            ).first()
        return (str(row[0]), row[1]) if row else None

    def run_tenant(self, run_id: str) -> str | None:
        """The tenant UUID that owns ``run_id``, or None when no such run exists."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text("select tenant_id::text from public.runs where id = :id"), {"id": run_id},
            ).first()
        return str(row[0]) if row and row[0] is not None else None

    def save_provenance(
        self, run_id: str, tenant_uuid: str, record: dict[str, Any],
        *, artifact_path: str | None, artifact_status: str,
        job_id: str | None = None, worker_id: str | None = None, attempt: int | None = None,
    ) -> bool:
        """Provenance as a row (P3-03); the same record is an object in run-artifacts.

        False when nothing was stored (lease lost, or the run already ended).
        """
        lease, lease_params = self._lease_clause(run_id, job_id, worker_id, attempt)
        with self._engine.begin() as conn:
            res = conn.execute(
                text(
                    "insert into public.run_provenance (run_id, tenant_id, classical_reference_hash, "
                    "calibration_hash, error_mitigation, record, artifact_path, artifact_status) "
                    "select cast(:id as text), cast(:t as uuid), cast(:h as text), cast(:c as text), "
                    "cast(:e as jsonb), cast(:r as jsonb), cast(:p as text), cast(:s as text) "
                    "where exists (select 1 from public.runs pr where pr.id = :id "
                    "and pr.status in ('queued', 'running'))" + lease + " "
                    "on conflict (run_id) do update set classical_reference_hash = excluded.classical_reference_hash, "
                    "calibration_hash = excluded.calibration_hash, error_mitigation = excluded.error_mitigation, "
                    "record = excluded.record, artifact_path = excluded.artifact_path, "
                    "artifact_status = excluded.artifact_status"
                ),
                {
                    "id": run_id, "t": tenant_uuid,
                    "h": str(record.get("classical_reference_hash") or ""),
                    "c": record.get("device_calibration_hash"),
                    "e": _dumps(record.get("error_mitigation_config"))
                    if record.get("error_mitigation_config") is not None else None,
                    "r": _dumps(record), "p": artifact_path, "s": artifact_status, **lease_params,
                },
            )
        return res.rowcount > 0

    def provenance(self, run_id: str, *, tenant_uuid: str | None = None) -> dict[str, Any] | None:
        sql = (
            "select classical_reference_hash, calibration_hash, error_mitigation, record, "
            "artifact_path, artifact_status from public.run_provenance where run_id = :id"
        )
        params: dict[str, Any] = {"id": run_id}
        if tenant_uuid is not None:
            sql += " and tenant_id = cast(:tenant as uuid)"
            params["tenant"] = tenant_uuid
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        return dict(row) if row else None

    def cancel_run(self, run_id: str) -> bool:
        """Cancel the run's open jobs; a running worker stops at its next heartbeat.

        Lock order: the run's job rows first, then the run row, as the
        janitor's dead-letter branch (reap_expired_jobs) and every
        lease-checked write do, so a cancel never deadlocks against them.
        """
        with self._engine.begin() as conn:
            conn.execute(
                text("select id from public.jobs where run_id = :id order by id for update"), {"id": run_id},
            )
            run = conn.execute(
                text("select tenant_id::text, status::text from public.runs where id = :id for update"),
                {"id": run_id},
            ).first()
            if run is None or run[1] in TERMINAL_RUN_STATUSES:
                return False
            conn.execute(
                text(
                    "update public.jobs set status = 'cancelled', finished_at = now(), "
                    "locked_by = null, locked_until = null "
                    "where run_id = :id and status in ('queued', 'running')"
                ),
                {"id": run_id},
            )
            conn.execute(
                text(
                    "update public.runs set status = 'canceled', completed_at = now(), "
                    "updated_at = now() where id = :id"
                ),
                {"id": run_id},
            )
            self._emit(conn, None, run_id, run[0], "status", _status("canceled"))
        return True

    # ── worker side ───────────────────────────────────────────────────

    def claim(self, worker_id: str, classes: Iterable[str], lease_seconds: int = 60) -> Job | None:
        with self._engine.begin() as conn:
            _as_service(conn)
            row = conn.execute(
                text(
                    "select id::text as id, tenant_id::text as tenant_id, run_id, kind, payload, "
                    "compute_class::text as compute_class, attempts, max_attempts "
                    "from public.claim_next_job(:w, cast(:c as public.compute_class[]), :l)"
                ),
                {"w": worker_id, "c": "{" + ",".join(classes) + "}", "l": lease_seconds},
            ).mappings().first()
        if row is None or row["id"] is None:
            return None
        return Job(
            id=row["id"], tenant_id=row["tenant_id"], run_id=row["run_id"], kind=row["kind"],
            payload=dict(row["payload"] or {}), compute_class=row["compute_class"],
            attempts=int(row["attempts"]), max_attempts=int(row["max_attempts"]),
        )

    def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int = 60, *, attempt: int) -> bool:
        """Renew the lease of this attempt; False when it no longer holds the job."""
        with self._engine.begin() as conn:
            _as_service(conn)
            return bool(conn.execute(
                text(
                    "select public.heartbeat_job(_job_id => cast(:j as uuid), _worker_id => :w, "
                    "_attempt => :a, _lease_seconds => :l)"
                ),
                {"j": job_id, "w": worker_id, "a": int(attempt), "l": lease_seconds},
            ).scalar_one())

    def complete(
        self, job_id: str, *, worker_id: str, attempt: int,
        result: dict[str, Any] | None = None, error: str | None = None,
    ) -> bool:
        """Complete a job this attempt holds the lease of (SF2); False when it doesn't."""
        with self._engine.begin() as conn:
            _as_service(conn)
            return bool(conn.execute(
                text(
                    "select public.complete_job(_job_id => cast(:j as uuid), _worker_id => :w, "
                    "_attempt => :a, _result => cast(:r as jsonb), _error => :e)"
                ),
                {"j": job_id, "w": worker_id, "a": int(attempt),
                 "r": _dumps(result) if result is not None else None, "e": error},
            ).scalar_one())

    def job_status(self, job_id: str) -> str | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("select status::text from public.jobs where id = cast(:j as uuid)"), {"j": job_id},
            ).first()
        return str(row[0]) if row else None

    def reap(self) -> int:
        """Janitor: requeue expired leases; dead-letter after max_attempts."""
        with self._engine.begin() as conn:
            _as_service(conn)
            return int(conn.execute(text("select public.reap_expired_jobs()")).scalar_one())

    # ── events ────────────────────────────────────────────────────────

    def emit(
        self, job: Job | None, run_id: str, tenant_uuid: str, type_: str, payload: dict[str, Any],
        *, worker_id: str | None = None, attempt: int | None = None,
    ) -> bool:
        """Append a run event. With a lease (``worker_id`` and ``attempt``), only
        while that attempt holds ``job``, the job of ``run_id`` (SF2)."""
        with self._engine.begin() as conn:
            if worker_id is not None or attempt is not None:
                if job is None:
                    raise ValueError("a lease needs the job")
                _, params = self._lease_clause(run_id, job.id, worker_id, attempt)
                held = conn.execute(text(f"select {self._LEASE}"), params).scalar_one()
                if not held:
                    return False
            self._emit(conn, job.id if job else None, run_id, tenant_uuid, type_, payload)
        return True

    @staticmethod
    def _emit(
        conn: Connection, job_id: str | None, run_id: str, tenant_uuid: str, type_: str, payload: dict[str, Any],
    ) -> None:
        conn.execute(
            text(
                "insert into public.job_events (job_id, run_id, tenant_id, type, payload) "
                "values (cast(:j as uuid), :r, cast(:t as uuid), :type, cast(:p as jsonb))"
            ),
            {"j": job_id, "r": run_id, "t": tenant_uuid, "type": type_, "p": _dumps(payload)},
        )

    def events(
        self, run_id: str, *, after_id: int = 0, tenant_uuid: str | None = None,
    ) -> list[JobEvent]:
        sql = "select id, run_id, type, payload, created_at from public.job_events where run_id = :r and id > :a"
        params: dict[str, Any] = {"r": run_id, "a": after_id}
        if tenant_uuid is not None:
            # SEC-H2: only events written under the run's own tenant.
            sql += " and tenant_id = cast(:tenant as uuid)"
            params["tenant"] = tenant_uuid
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql + " order by id"), params).mappings().all()
        return [
            JobEvent(id=int(r["id"]), run_id=r["run_id"], type=r["type"],
                     payload=dict(r["payload"] or {}), created_at=r["created_at"])
            for r in rows
        ]


def _status(status: str) -> dict[str, Any]:
    return {"type": "status", "status": status, "at": datetime.now(UTC).isoformat()}


def _run(row: Any) -> RunRecord:
    return RunRecord(
        id=row["id"], tenant_id=row["tenant_id"], status=row["status"], label=row["label"],
        config=dict(row["config"] or {}), created_at=row["created_at"],
        started_at=row["started_at"], completed_at=row["completed_at"],
        client_run_id=row.get("client_run_id"),
    )


_QUEUE: JobQueue | None = None


def get_queue() -> JobQueue:
    global _QUEUE
    if _QUEUE is None:
        _QUEUE = JobQueue()
    return _QUEUE


def reset_queue() -> None:
    global _QUEUE
    _QUEUE = None


__all__ = [
    "COMPUTE_CLASSES",
    "JOB_KINDS",
    "TERMINAL_RUN_STATUSES",
    "Job",
    "JobEvent",
    "JobQueue",
    "RunRecord",
    "get_queue",
    "reset_queue",
]
