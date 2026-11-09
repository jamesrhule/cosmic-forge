"""``.github/workflows/staging-db.yml`` (LEDGER Decision 20).

The staging migrations and admin seed run in the ``staging`` environment with
a read-only token; each secret reaches only the step that uses it; every
action is pinned to a commit; and the steps are the P3-01 runner, then the
seed, on a locked install.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from ucgle_f1.db import migrate as migrate_mod
from ucgle_f1.db import staging

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "staging-db.yml"
CI = REPO / ".github" / "workflows" / "ci.yml"
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
USES_LINE = re.compile(r"^\s*-?\s*uses:\s*(?P<ref>\S+)(?P<rest>.*)$")
TAG_COMMENT = re.compile(r"^\s+# v\d+\.\d+\.\d+$")
SECRET_REF = re.compile(r"\$\{\{\s*secrets\.([A-Z0-9_]+)\s*\}\}")
MIGRATE = "python -m ucgle_f1.db.staging migrate"
SEED = "python -m ucgle_f1.db.staging seed-admin"


def _wf() -> dict[Any, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _on(wf: dict[Any, Any]) -> dict[str, Any]:
    # YAML 1.1 reads a bare `on` key as the boolean True.
    return wf.get("on", wf.get(True))  # type: ignore[no-any-return]


def _steps() -> list[dict[str, Any]]:
    return [st for job in _wf()["jobs"].values() for st in job.get("steps", [])]


def _step(command: str) -> tuple[int, dict[str, Any]]:
    found = [(i, st) for i, st in enumerate(_steps()) if command in str(st.get("run", ""))]
    assert len(found) == 1, f"exactly one step runs {command!r}"
    return found[0]


def _walk(node: Any, path: tuple[Any, ...] = ()) -> list[tuple[tuple[Any, ...], str]]:
    if isinstance(node, dict):
        return [hit for k, v in node.items() for hit in _walk(v, (*path, k))]
    if isinstance(node, list):
        return [hit for i, v in enumerate(node) for hit in _walk(v, (*path, i))]
    return [(path, node)] if isinstance(node, str) else []


def test_triggers_are_call_and_dispatch_only() -> None:
    assert set(_on(_wf())) == {"workflow_call", "workflow_dispatch"}


def test_a_caller_must_pass_each_secret_by_name() -> None:
    """A secret the caller does not pass is empty in a called workflow (GitHub docs)."""
    call = _on(_wf())["workflow_call"]
    assert call["secrets"] == {name: {"required": True} for name in staging.SEED_NEEDS}
    assert "inputs" not in call  # who becomes admin is committed, not an input


def test_token_is_read_only() -> None:
    wf = _wf()
    assert wf["permissions"] == {"contents": "read"}
    for name, job in wf["jobs"].items():
        assert job.get("permissions", {"contents": "read"}) == {"contents": "read"}, name


def test_every_job_runs_in_the_staging_environment() -> None:
    for name, job in _wf()["jobs"].items():
        env = job.get("environment")
        assert (env if isinstance(env, str) else (env or {}).get("name")) == "staging", name


def test_one_run_at_a_time() -> None:
    for name, job in _wf()["jobs"].items():
        assert job["concurrency"] == {"group": "staging-db", "cancel-in-progress": False}, name


def test_secrets_appear_only_in_step_level_env() -> None:
    wf = _wf()
    hits = [(path, value) for path, value in _walk(wf) if "secrets" in value]
    assert hits, "the workflow reads the staging secrets"
    for path, value in hits:
        assert len(path) == 6, path
        assert (path[0], path[2], path[4]) == ("jobs", "steps", "env"), path
        # The whole value is one secret, under its own Part 6 name.
        assert SECRET_REF.fullmatch(value), (path, value)
        assert SECRET_REF.fullmatch(value).group(1) == path[5], path  # type: ignore[union-attr]
    assert "secrets.DATABASE_URL" not in json.dumps(wf.get("env", {}))
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets: inherit" not in text


def test_each_step_gets_only_the_secrets_it_needs() -> None:
    by_step: dict[int, set[str]] = {}
    for i, st in enumerate(_steps()):
        names = {
            m.group(1) for v in (st.get("env") or {}).values() for m in SECRET_REF.finditer(str(v))
        }
        if names:
            by_step[i] = names
    migrate_at, _ = _step(MIGRATE)
    seed_at, _ = _step(SEED)
    assert by_step == {migrate_at: set(staging.MIGRATE_NEEDS), seed_at: set(staging.SEED_NEEDS)}
    assert set(staging.SEED_NEEDS) == {"DATABASE_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}


def test_no_run_script_handles_a_secret_itself() -> None:
    names = set(staging.SEED_NEEDS)
    for st in _steps():
        run = str(st.get("run", ""))
        assert "${{" not in run or "secrets" not in run
        for name in names:
            assert f"${name}" not in run and f"${{{name}}}" not in run, (name, run)


def test_actions_are_pinned_to_a_commit_with_the_tag_in_a_comment() -> None:
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    uses = [m for m in map(USES_LINE.match, lines) if m]
    assert len(uses) >= 2
    for m in uses:
        assert PINNED.match(m.group("ref")), m.group(0)
        assert TAG_COMMENT.match(m.group("rest")), m.group(0)
    assert all(PINNED.match(st["uses"]) for st in _steps() if "uses" in st)


def test_checkout_keeps_no_credentials_and_uv_restores_no_cache() -> None:
    steps = _steps()
    checkout = [st for st in steps if str(st.get("uses", "")).startswith("actions/checkout@")]
    setup_uv = [st for st in steps if str(st.get("uses", "")).startswith("astral-sh/setup-uv@")]
    assert len(checkout) == 1 and checkout[0]["with"]["persist-credentials"] is False
    assert len(setup_uv) == 1 and setup_uv[0]["with"]["enable-cache"] is False


def test_uv_and_python_are_pinned_as_in_ci() -> None:
    wf, ci = _wf(), yaml.safe_load(CI.read_text(encoding="utf-8"))
    for name in ("UV_VERSION", "PYTHON_VERSION"):
        assert wf["env"][name] == ci["env"][name], name
    assert re.fullmatch(r"\d+\.\d+\.\d+", wf["env"]["UV_VERSION"])
    setup_uv = next(
        st for st in _steps() if str(st.get("uses", "")).startswith("astral-sh/setup-uv@")
    )
    assert setup_uv["with"]["version"] == "${{ env.UV_VERSION }}"
    assert any('uv python install "$PYTHON_VERSION"' in str(st.get("run", "")) for st in _steps())


def test_install_is_locked_and_the_runner_then_the_seed_run_on_it() -> None:
    steps = _steps()
    sync = [i for i, st in enumerate(steps) if "uv sync" in str(st.get("run", ""))]
    assert len(sync) == 1
    assert "--frozen" in steps[sync[0]]["run"].split()
    migrate_at, migrate_step = _step(MIGRATE)
    seed_at, seed_step = _step(SEED)
    assert sync[0] < migrate_at < seed_at
    for st in (migrate_step, seed_step):
        # The locked environment as installed; `uv run` must not re-resolve it.
        assert st["run"].startswith("uv run --no-sync python -m ucgle_f1.db.staging ")
    # The migrate command is the P3-01 runner.
    assert staging.apply_migrations is migrate_mod.apply_migrations
