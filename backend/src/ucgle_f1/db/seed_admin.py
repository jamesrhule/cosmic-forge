"""Seed the product's admin user and its admin role (LEDGER Decision 20).

The admin is one Supabase Auth user, ``ADMIN_EMAIL``, holding the ``admin``
row in ``public.user_roles``: the table ``public.has_role()`` reads, the
frontend's ``hasRole()`` reads (``src/lib/auth.tsx``) and the verdict API's
``require_supabase_admin`` reads (correction 9,
``ucgle_f1.m8_agent.supabase_auth``). Nothing new models "admin".

- **The user** comes from Supabase Auth's Admin API (``/auth/v1/admin/users``)
  with the service-role key. It is created with ``email_confirm: true`` and no
  password; Supabase Auth then stores a random password nobody knows, and the
  admin signs in through an emailed link: a magic link or one-time code, or
  the app's "forgot password" flow (``/reset-password``), which is the only
  emailed-link sign-in the app's UI offers today. A user that already has the
  email (it signed up, or an earlier run created it) is reused unchanged.
- **The role** is inserted over ``DATABASE_URL``, the connection the P3-01
  runner uses, as the ``service_role`` database role when that connection may
  assume it (``set local role``), otherwise as the connection's own role.
  ``on conflict (user_id, role) do nothing`` makes it idempotent.
  ``granted_by`` stays null: no user granted it, the deploy job did.

Keys: ``sb_secret_…`` keys are not JWTs and go on the ``apikey`` header only,
as Supabase's API-key guide says; a legacy JWT service-role key also goes on
``Authorization: Bearer``. Nothing here prints or logs a key (R9). The CLI
entry point, with the missing-secret handling, is :mod:`ucgle_f1.db.staging`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx
import psycopg

# The product's admin (LEDGER Decision 20). A committed value, not a workflow
# input, so who becomes admin changes only through a reviewed commit.
ADMIN_EMAIL = "jamesrhule@projecthumancity.com"

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PER_PAGE = 200
_MAX_PAGES = 500  # 100 000 users: far beyond staging; a guard against a looping API


class SeedError(RuntimeError):
    """The seed cannot finish; the message names the cause, never a secret."""


@dataclass(frozen=True)
class SeedResult:
    user_id: str
    user_created: bool
    email_confirmed: bool
    role_granted: bool
    db_role: str


def valid_email(email: str) -> str:
    email = email.strip().lower()
    if not _EMAIL.match(email):
        raise SeedError("the admin email is not an email address")
    return email


def https_base(supabase_url: str) -> str:
    """``SUPABASE_URL`` without a trailing slash; only https carries the key."""
    base = supabase_url.strip().rstrip("/")
    parts = urlsplit(base)
    if parts.scheme != "https" or not parts.hostname or parts.path or parts.query:
        raise SeedError("SUPABASE_URL must be the project's https:// URL (https://<ref>.supabase.co)")
    return base


def _is_jwt(key: str) -> bool:
    return key.count(".") == 2 and key.startswith("eyJ")


class AuthAdmin:
    """The two Supabase Auth Admin API calls the seed needs.

    ``transport`` replaces the network in tests (``httpx.MockTransport``).
    """

    def __init__(self, supabase_url: str, service_role_key: str, *,
                 transport: httpx.BaseTransport | None = None, timeout: float = 15.0) -> None:
        headers = {"apikey": service_role_key}
        if _is_jwt(service_role_key):
            headers["Authorization"] = f"Bearer {service_role_key}"
        self._client = httpx.Client(
            base_url=https_base(supabase_url) + "/auth/v1",
            headers=headers,
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
        )

    def __enter__(self) -> AuthAdmin:
        return self

    def __exit__(self, *exc: object) -> None:
        self._client.close()

    @staticmethod
    def _body(resp: httpx.Response) -> dict[str, Any]:
        try:
            body = resp.json()
        except ValueError:
            return {}
        return body if isinstance(body, dict) else {}

    def _fail(self, what: str, resp: httpx.Response) -> SeedError:
        body = self._body(resp)
        code = str(body.get("error_code") or body.get("code") or "")
        return SeedError(f"Supabase Auth {what} failed: HTTP {resp.status_code} {code}".rstrip())

    def find_user(self, email: str, *, use_filter: bool = True) -> dict[str, Any] | None:
        """The user whose email is ``email`` (case-insensitive), or None."""
        for page in range(1, _MAX_PAGES + 1):
            params: dict[str, str | int] = {"page": page, "per_page": _PER_PAGE}
            if use_filter:
                # Narrows the listing server-side; the match below is exact.
                params["filter"] = email
            resp = self._client.get("/admin/users", params=params)
            if resp.status_code != 200:
                raise self._fail("user lookup", resp)
            users = self._body(resp).get("users")
            if not isinstance(users, list):
                raise SeedError("Supabase Auth user lookup returned no user list")
            for user in users:
                if isinstance(user, dict) and str(user.get("email") or "").lower() == email:
                    return user
            if len(users) < _PER_PAGE:
                return None
        raise SeedError(f"Supabase Auth user lookup did not end after {_MAX_PAGES} pages")

    def create_user(self, email: str) -> dict[str, Any] | None:
        """Create a confirmed user with no password; None if the email exists."""
        resp = self._client.post("/admin/users", json={"email": email, "email_confirm": True})
        if resp.status_code == 422 and self._body(resp).get("error_code") == "email_exists":
            return None
        if resp.status_code not in (200, 201):
            raise self._fail("user creation", resp)
        return self._body(resp)


def ensure_admin_user(auth: AuthAdmin, email: str) -> tuple[dict[str, Any], bool]:
    """The admin's Auth user, created if absent; returns (user, created)."""
    user = auth.find_user(email)
    if user is not None:
        return user, False
    created = auth.create_user(email)
    if created is not None:
        return created, True
    # Created between the lookup and the create, or the filter missed it.
    user = auth.find_user(email, use_filter=False)
    if user is None:
        raise SeedError("Supabase Auth reports the email exists but lists no such user")
    return user, False


def _libpq(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def grant_admin_role(database_url: str, user_id: str) -> tuple[bool, str]:
    """Insert ``(user_id, 'admin')`` into ``public.user_roles``; returns (granted, db_role)."""
    with psycopg.connect(_libpq(database_url)) as conn, conn.transaction():
        row = conn.execute(
            "select case when exists (select 1 from pg_roles where rolname = 'service_role')"
            " then pg_has_role(current_user, 'service_role', 'MEMBER') else false end"
        ).fetchone()
        if row is not None and row[0]:
            conn.execute("set local role service_role")
        who = conn.execute("select current_user").fetchone()
        db_role = str(who[0]) if who else "?"
        try:
            inserted = conn.execute(
                "insert into public.user_roles (user_id, role)"
                " values (%s, 'admin'::public.app_role)"
                " on conflict (user_id, role) do nothing returning id",
                (user_id,),
            ).fetchone()
        except psycopg.errors.ForeignKeyViolation as exc:
            raise SeedError(
                f"user {user_id} is not in auth.users of DATABASE_URL: "
                "SUPABASE_URL and DATABASE_URL name different projects"
            ) from exc
    return inserted is not None, db_role


def seed_admin(
    *,
    database_url: str,
    supabase_url: str,
    service_role_key: str,
    email: str = ADMIN_EMAIL,
    transport: httpx.BaseTransport | None = None,
) -> SeedResult:
    """Ensure the admin user exists and holds the admin role. Idempotent."""
    email = valid_email(email)
    with AuthAdmin(supabase_url, service_role_key, transport=transport) as auth:
        user, created = ensure_admin_user(auth, email)
    user_id = str(user.get("id") or "")
    if not user_id:
        raise SeedError("Supabase Auth returned a user without an id")
    granted, db_role = grant_admin_role(database_url, user_id)
    return SeedResult(
        user_id=user_id,
        user_created=created,
        email_confirmed=bool(user.get("email_confirmed_at") or user.get("confirmed_at")),
        role_granted=granted,
        db_role=db_role,
    )


__all__ = [
    "ADMIN_EMAIL",
    "AuthAdmin",
    "SeedError",
    "SeedResult",
    "ensure_admin_user",
    "grant_admin_role",
    "https_base",
    "seed_admin",
    "valid_email",
]
