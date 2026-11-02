"""Run artefacts in Supabase Storage (P3-03): the ``run-artifacts`` bucket.

Objects are named ``<run_id>/<file>`` (main's bucket policies key on the
first path segment). Uploads use the Storage REST API with the service-role
key from the environment (R9). Without ``SUPABASE_URL`` and
``SUPABASE_SERVICE_ROLE_KEY`` nothing is uploaded and the caller records
``BLOCKED-ON-JAMES:SUPABASE_SERVICE_ROLE_KEY`` (R14); the database row still
holds the record, so nothing is lost.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from ._paths import safe_component

BUCKET = "run-artifacts"
BLOCKED = "BLOCKED-ON-JAMES:SUPABASE_SERVICE_ROLE_KEY"


@dataclass(frozen=True)
class Upload:
    path: str | None
    status: str  # "stored" | "BLOCKED-ON-JAMES:…" | "failed: …"


class ArtifactStore:
    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    @staticmethod
    def configured() -> bool:
        return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))

    def put(self, run_id: str, name: str, data: bytes, content_type: str = "application/json") -> Upload:
        path = f"{safe_component(run_id, 'run id')}/{safe_component(name, 'artifact name')}"
        url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return Upload(None, BLOCKED)
        try:
            with httpx.Client(transport=self._transport, timeout=30.0) as client:
                resp = client.post(
                    f"{url}/storage/v1/object/{BUCKET}/{path}",
                    content=data,
                    headers={
                        "Authorization": f"Bearer {key}", "apikey": key,
                        "Content-Type": content_type, "x-upsert": "true",
                    },
                )
        except httpx.HTTPError as exc:
            return Upload(None, f"failed: {exc.__class__.__name__}")
        if resp.status_code >= 400:
            return Upload(None, f"failed: HTTP {resp.status_code}")
        return Upload(f"{BUCKET}/{path}", "stored")

    def delete(self, stored_path: str) -> bool:
        """Remove an object ``put`` stored (``Upload.path``); True when it is gone.

        Storage's ``DELETE /object/<bucket>/<name>``. A missing object counts
        as gone; any other failure, or a path ``put`` can't have returned,
        is False (the caller logs it).
        """
        bucket, _, rest = stored_path.partition("/")
        run_id, _, name = rest.partition("/")
        try:
            path = f"{safe_component(run_id, 'run id')}/{safe_component(name, 'artifact name')}"
        except ValueError:
            return False
        if bucket != BUCKET:
            return False
        url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return False
        try:
            with httpx.Client(transport=self._transport, timeout=30.0) as client:
                resp = client.delete(
                    f"{url}/storage/v1/object/{BUCKET}/{path}",
                    headers={"Authorization": f"Bearer {key}", "apikey": key},
                )
        except httpx.HTTPError:
            return False
        return resp.status_code < 400 or resp.status_code == 404


__all__ = ["BLOCKED", "BUCKET", "ArtifactStore", "Upload"]
