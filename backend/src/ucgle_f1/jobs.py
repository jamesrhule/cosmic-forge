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
    ) -> str:
        """Check the tenant's plan limits (P3-05), then insert the run row and
        its job atomically; return the job id."""
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
                    "insert into public.runs (id, tenant_id, visibility, status, label, config, precision) "
                    "values (:id, cast(:tenant as uuid), 'private', 'queued', :label, "
                    "cast(:config as jsonb), :precision)"
                ),
                {
                    "id": run_id, "tenant": tenant_uuid, "label": label,
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

    def get_run(self, run_id: str, *, tenant_uuid: str | None = None) -> RunRecord | None:
        sql = (
            "select id, tenant_id::text as tenant_id, status::text as status, coalesce(label, '') as label, "
            "config, created_at, started_at, completed_at from public.runs where id = :id"
        )
        params: dict[str, Any] = {"id": run_id}
        if tenant_uuid is not None:
            sql += " and tenant_id = cast(:tenant as uuid)"
            params["tenant"] = tenant_uuid
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        return _run(row) if row else None

    def list_runs(
        self, *, tenant_uuid: str, domain: str | None = None, limit: int = 100, offset: int = 0,
    ) -> list[RunRecord]:
        sql = (
            "select id, tenant_id::text as tenant_id, status::text as status, coalesce(label, '') as label, "
            "config, created_at, started_at, completed_at from public.runs "
            "where tenant_id = cast(:tenant as uuid)"
        )
        params: dict[str, Any] = {"tenant": tenant_uuid, "limit": limit, "offset": offset}
        if domain is not None:
            sql += " and config ->> 'domain' = :domain"
            params["domain"] = domain
        sql += " order by created_at desc, id desc limit :limit offset :offset"
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [_run(r) for r in rows]

    def set_run_status(self, run_id: str, status: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "update public.runs set status = cast(:s as public.run_status), "
                    "started_at = case when :s = 'running' then coalesce(started_at, now()) else started_at end, "
                    "completed_at = case when :s in ('completed', 'failed', 'canceled') then now() "
                    "else completed_at end, updated_at = now() where id = :id"
                ),
                {"s": status, "id": run_id},
            )

    def save_result(self, run_id: str, payload: dict[str, Any]) -> None:
        """Store the full result payload (P3-03); returned verbatim by the API."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "insert into public.run_results (run_id, payload) values (:id, cast(:p as jsonb)) "
                    "on conflict (run_id) do update set payload = excluded.payload, updated_at = now()"
                ),
                {"id": run_id, "p": _dumps(payload)},
            )

    @staticmethod
    def _result_sql(column: str, tenant_uuid: str | None) -> tuple[str, dict[str, Any]]:
        # SEC-H2: with a tenant, the result is returned only when the run
        # itself belongs to that tenant.
        if tenant_uuid is None:
            return f"select {column} from public.run_results where run_id = :id", {}
        return (
            f"select rr.{column} from public.run_results rr join public.runs r on r.id = rr.run_id "
            "where rr.run_id = :id and r.tenant_id = cast(:tenant as uuid)",
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
    ) -> None:
        """Provenance as a row (P3-03); the same record is an object in run-artifacts."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "insert into public.run_provenance (run_id, tenant_id, classical_reference_hash, "
                    "calibration_hash, error_mitigation, record, artifact_path, artifact_status) "
                    "values (:id, cast(:t as uuid), :h, :c, cast(:e as jsonb), cast(:r as jsonb), :p, :s) "
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
                    "r": _dumps(record), "p": artifact_path, "s": artifact_status,
                },
            )

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
        """Cancel the run's open jobs; a running worker stops at its next heartbeat."""
        with self._engine.begin() as conn:
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

    def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int = 60) -> bool:
        with self._engine.begin() as conn:
            _as_service(conn)
            return bool(conn.execute(
                text("select public.heartbeat_job(cast(:j as uuid), :w, :l)"),
                {"j": job_id, "w": worker_id, "l": lease_seconds},
            ).scalar_one())

    def complete(self, job_id: str, *, result: dict[str, Any] | None = None, error: str | None = None) -> None:
        with self._engine.begin() as conn:
            _as_service(conn)
            conn.execute(
                text("select public.complete_job(cast(:j as uuid), cast(:r as jsonb), :e)"),
                {"j": job_id, "r": _dumps(result) if result is not None else None, "e": error},
            )

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

    def emit(self, job: Job | None, run_id: str, tenant_uuid: str, type_: str, payload: dict[str, Any]) -> None:
        with self._engine.begin() as conn:
            self._emit(conn, job.id if job else None, run_id, tenant_uuid, type_, payload)

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
