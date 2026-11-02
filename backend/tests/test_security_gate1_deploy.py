"""Gate 1 round 3 (c6): the deploy workflow keeps the Cloudflare token away
from build code, uses no shared bun cache, passes secrets at step level only
and deploys production only from main or a release tag.

- SEC-M2 residual: at 9c6bf4c the secret-free build step and the
  token-holding wrangler step shared one job and one workspace, so a build
  dependency could add ``"build": {"command": ...}`` to
  dist/server/wrangler.json and wrangler ran it with CLOUDFLARE_API_TOKEN in
  its environment. ``test_m2_planted_wrangler_config_never_runs_next_to_the_token``
  plants such configs and runs the token job's steps that follow the build
  hand-over, with the real locked wrangler (``--dry-run``).
- The branch guard is checked by evaluating each job's ``if`` with a small
  GitHub-expression evaluator, for pushes, tags, dispatches and calls.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
DEPLOY = REPO / ".github" / "workflows" / "deploy.yml"
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


def _wf() -> dict[str, Any]:
    return yaml.safe_load(DEPLOY.read_text(encoding="utf-8"))


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return list(job.get("steps", []))


def _uses(step: dict[str, Any], action: str) -> bool:
    return str(step.get("uses", "")).split("@", 1)[0] == action


def _token_job(wf: dict[str, Any]) -> tuple[str, dict[str, Any], int]:
    holders = [
        (name, job, i)
        for name, job in wf["jobs"].items()
        for i, st in enumerate(_steps(job))
        if "secrets.CLOUDFLARE_API_TOKEN }}" in json.dumps(st.get("env", {}))
    ]
    assert len(holders) == 1, "exactly one step receives the Cloudflare token"
    return holders[0]


def _build_jobs(wf: dict[str, Any]) -> list[str]:
    return [
        name
        for name, job in wf["jobs"].items()
        if any("bun run build" in str(st.get("run", "")) for st in _steps(job))
    ]


# ── A small evaluator for GitHub Actions expressions ────────────────────────
# Enough of https://docs.github.com/actions/learn-github-actions/expressions
# for the deploy guards: literals, property paths, ( ), !, ==, !=, &&, ||
# (which return operands, as in GitHub) and startsWith. String comparison
# ignores case, as GitHub's does.

_TOKEN = re.compile(
    r"\s*(?:(?P<str>'(?:[^']|'')*')|(?P<op>==|!=|&&|\|\||[()!,])|(?P<num>\d+(?:\.\d+)?)"
    r"|(?P<id>[A-Za-z_][\w-]*(?:\.[A-Za-z_][\w-]*)*))"
)


def _tokens(src: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    src = src.strip()
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        assert m and m.end() > pos, f"cannot parse expression at {src[pos:]!r}"
        kind = m.lastgroup or ""
        out.append((kind, m.group(kind)))
        pos = m.end()
    return out


def _truthy(v: Any) -> bool:
    if isinstance(v, float) and math.isnan(v):
        return False
    return v not in (None, False, 0, "")


def _number(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, int | float):
        return float(v)
    try:
        return float(v.strip() or 0)
    except ValueError:
        return math.nan


def _equal(a: Any, b: Any) -> bool:
    if isinstance(a, str) and isinstance(b, str):
        return a.casefold() == b.casefold()
    if type(a) is type(b):
        return bool(a == b)
    return _number(a) == _number(b)


class _Eval:
    def __init__(self, src: str, ctx: dict[str, Any]) -> None:
        src = src.strip()
        if src.startswith("${{") and src.endswith("}}"):
            src = src[3:-2]
        self.toks, self.i, self.ctx = _tokens(src), 0, ctx

    def peek(self) -> str | None:
        return self.toks[self.i][1] if self.i < len(self.toks) else None

    def take(self, want: str | None = None) -> tuple[str, str]:
        tok = self.toks[self.i]
        assert want is None or tok[1] == want, f"expected {want!r}, got {tok[1]!r}"
        self.i += 1
        return tok

    def run(self) -> Any:
        value = self.or_()
        assert self.i == len(self.toks), f"trailing tokens: {self.toks[self.i:]}"
        return value

    def or_(self) -> Any:
        value = self.and_()
        while self.peek() == "||":
            self.take()
            right = self.and_()
            value = value if _truthy(value) else right
        return value

    def and_(self) -> Any:
        value = self.eq()
        while self.peek() == "&&":
            self.take()
            right = self.eq()
            value = right if _truthy(value) else value
        return value

    def eq(self) -> Any:
        value = self.unary()
        while self.peek() in ("==", "!="):
            op = self.take()[1]
            right = self.unary()
            value = _equal(value, right) == (op == "==")
        return value

    def unary(self) -> Any:
        if self.peek() == "!":
            self.take()
            return not _truthy(self.unary())
        return self.primary()

    def primary(self) -> Any:
        kind, text = self.take()
        if text == "(":
            value = self.or_()
            self.take(")")
            return value
        if kind == "str":
            return text[1:-1].replace("''", "'")
        if kind == "num":
            return float(text)
        if text in ("true", "false", "null"):
            return {"true": True, "false": False, "null": None}[text]
        if self.peek() == "(":
            self.take("(")
            args = [self.or_()]
            while self.peek() == ",":
                self.take()
                args.append(self.or_())
            self.take(")")
            assert text == "startsWith", f"function {text} not supported here"
            return str(args[0] or "").casefold().startswith(str(args[1] or "").casefold())
        value: Any = self.ctx
        for part in text.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        return value


def _evaluate(expr: str, ctx: dict[str, Any]) -> Any:
    return _Eval(expr, ctx).run()


def test_expression_evaluator_follows_github_semantics() -> None:
    ctx = {"inputs": {}, "github": {"ref": "refs/tags/qcompass-v1.0.0"}}
    assert _evaluate("inputs.environment || 'staging'", ctx) == "staging"
    tag_env = "(startsWith(github.ref, 'refs/tags/') && 'production') || 'x'"
    assert _evaluate(tag_env, ctx) == "production"
    assert _evaluate("'Production' == 'production'", ctx) is True
    assert _evaluate("!(1 == 1) || ''", ctx) == ""


# ── SEC-M2 residual ─────────────────────────────────────────────────────────


def _resolve(value: Any) -> str:
    """A step/job env value with its expressions replaced by test values."""
    text = str(value)
    text = re.sub(r"\$\{\{\s*secrets\.(\w+)\s*\}\}", lambda m: f"fake-{m.group(1)}", text)
    return re.sub(r"\$\{\{.*?\}\}", "https://api.example.test", text)


def _config_path(run: str, env: dict[str, str]) -> str:
    m = re.search(r"--config\s+(\"?)(\S+?)\1(?:\s|$)", run)
    assert m, "the deploy step passes the wrangler config explicitly"
    return re.sub(r"\$\{?(\w+)\}?", lambda v: env[v.group(1)], m.group(2))


_CLEAN = {"name": "x", "main": "index.js", "compatibility_date": "2025-09-24", "no_bundle": True}


def _planted(leak: Path) -> dict[str, tuple[dict[str, Any] | str | None, str | None]]:
    command = {"command": f'echo "token=$CLOUDFLARE_API_TOKEN" > {leak}'}
    return {
        "build at the top level": ({**_CLEAN, "build": command}, None),
        "build in an environment": ({**_CLEAN, "env": {"staging": {"build": command}}}, None),
        "container image build": (
            {**_CLEAN, "containers": [{"class_name": "C", "image": "./Dockerfile"}]},
            None,
        ),
        "capnp compile": ({**_CLEAN, "unsafe": {"capnp": {"source_schemas": ["x.capnp"]}}}, None),
        "a .env wrangler would load": (_CLEAN, "CLOUDFLARE_API_BASE_URL=http://127.0.0.1:9/\n"),
        "no config": (None, None),
        "not JSON": ("{ build: { command: 'x' } }", None),
    }


def _run_after_handover(
    tmp_path: Path, config: dict[str, Any] | str | None, dotenv: str | None
) -> tuple[int, list[str], bool, str]:
    """Run the token job's run-steps after the build hand-over, as the runner would.

    Returns (exit code of the first failing step or 0, names of the steps
    that ran, whether the token step ran, its output or the step summary).
    """
    wf = _wf()
    job_name, job, token_index = _token_job(wf)
    steps = _steps(job)
    handover = [i for i, st in enumerate(steps) if _uses(st, "actions/download-artifact")]
    if not handover:  # no hand-over: the build ran in this job
        handover = [i for i, st in enumerate(steps) if "bun run build" in str(st.get("run", ""))]
    assert handover, f"{job_name}: no build hand-over found"
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "node_modules").symlink_to(REPO / "node_modules")
    summary = tmp_path / "summary.md"
    base_env = {k: v for k, v in os.environ.items() if not k.startswith(("CLOUDFLARE_", "GITHUB_"))}
    base_env.update(
        TARGET_ENV="staging",
        GITHUB_STEP_SUMMARY=str(summary),
        GITHUB_OUTPUT=str(tmp_path / "output"),
        WRANGLER_SEND_METRICS="false",
        CI="true",
    )
    base_env.update({k: _resolve(v) for k, v in (wf.get("env") or {}).items()})
    base_env.update({k: _resolve(v) for k, v in (job.get("env") or {}).items()})
    token_step = steps[token_index]
    token_env = {**base_env, **{k: _resolve(v) for k, v in (token_step.get("env") or {}).items()}}
    cfg = ws / _config_path(str(token_step["run"]), token_env)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    worker = "export default { fetch() { return new Response('ok') } }\n"
    (cfg.parent / "index.js").write_text(worker)
    if isinstance(config, dict):
        cfg.write_text(json.dumps(config))
    elif isinstance(config, str):
        cfg.write_text(config)
    if dotenv is not None:
        (ws / ".env").write_text(dotenv)
    ran: list[str] = []
    for i in range(handover[-1] + 1, token_index + 1):
        st = steps[i]
        assert "uses" not in st, f"{job_name}: an action runs on the build output before the deploy"
        run = re.sub(r"\$\{\{.*?\}\}", "placeholder", str(st["run"]))
        if i == token_index:
            run = run.replace("wrangler deploy", "wrangler deploy --dry-run")
        env = {**base_env, **{k: _resolve(v) for k, v in (st.get("env") or {}).items()}}
        script = tmp_path / f"step{i}.sh"
        script.write_text(run)
        proc = subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
            cwd=ws,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        ran.append(str(st.get("name", f"step {i}")))
        if proc.returncode != 0:
            return proc.returncode, ran, i == token_index, proc.stdout + proc.stderr
    return 0, ran, True, summary.read_text() if summary.exists() else ""


@pytest.mark.parametrize("case", list(_planted(Path("leak")).keys()))
def test_m2_planted_wrangler_config_never_runs_next_to_the_token(tmp_path: Path, case: str) -> None:
    assert (REPO / "node_modules" / ".bin" / "wrangler").exists(), "run `bun install` first"
    leak = tmp_path / "leak.txt"
    config, dotenv = _planted(leak)[case]
    code, ran, token_step_ran, output = _run_after_handover(tmp_path, config, dotenv)
    assert not leak.exists(), f"{case}: planted command ran with the token: {leak.read_text()}"
    assert code != 0, f"{case}: the deploy went ahead (steps run: {ran})"
    assert not token_step_ran, f"{case}: wrangler held the token: {output[-300:]}"


def test_m2_clean_build_output_deploys(tmp_path: Path) -> None:
    """Positive control: the refusal does not block a config with no command."""
    assert (REPO / "node_modules" / ".bin" / "wrangler").exists(), "run `bun install` first"
    code, ran, token_step_ran, output = _run_after_handover(tmp_path, _CLEAN, None)
    assert code == 0 and token_step_ran, f"steps run: {ran}: {output[-800:]}"
    assert "deployed" in output


def test_m2_build_and_deploy_are_separate_jobs() -> None:
    wf = _wf()
    deploy_name, deploy, token_index = _token_job(wf)
    builds = _build_jobs(wf)
    assert len(builds) == 1, f"one job builds the workbench: {builds}"
    (build_name,) = builds
    assert build_name != deploy_name, "build never shares a job (runner, workspace) with the token"
    build = wf["jobs"][build_name]

    # The build job holds nothing: no environment, no secret, read-only token.
    assert "environment" not in build, "no environment: environment secrets stay out of reach"
    assert "secrets." not in json.dumps(build), f"{build_name} references a secret"
    assert build["permissions"] == {"contents": "read"}
    assert not any("wrangler" in str(st.get("run", "")) for st in _steps(build))
    uploads = [st for st in _steps(build) if _uses(st, "actions/upload-artifact")]
    assert len(uploads) == 1 and PINNED.match(uploads[0]["uses"])
    assert uploads[0]["with"]["path"].rstrip("/") == "dist"

    # The deploy job starts afresh and takes only dist/ from the build.
    needs = deploy["needs"] if isinstance(deploy["needs"], list) else [deploy["needs"]]
    assert build_name in needs
    steps = _steps(deploy)
    assert "secrets." not in json.dumps(deploy.get("env", {}))
    order = {}
    for i, st in enumerate(steps):
        run = str(st.get("run", ""))
        build_code = re.search(r"\bbun(x| x| run)\b|\bvite\b|\bnpx\b", run)
        assert not build_code, f"build code in {deploy_name}: {run}"
        if i != token_index:
            assert "secrets." not in json.dumps(st), f"{deploy_name} step {i} sees a secret"
        if _uses(st, "actions/checkout"):
            assert st.get("with", {}).get("persist-credentials") is False
            order.setdefault("checkout", i)
        if _uses(st, "oven-sh/setup-bun"):
            assert st["with"].get("no-cache") is True
            order.setdefault("setup-bun", i)
        if "bun install" in run:
            assert "bun install --frozen-lockfile --ignore-scripts" in run
            order.setdefault("install", i)
        if _uses(st, "actions/download-artifact"):
            assert PINNED.match(st["uses"])
            assert str(st["with"]["path"]).rstrip("/") == "dist"
            assert f"needs.{build_name}.outputs." in str(st["with"].get("artifact-ids", ""))
            order.setdefault("download", i)
        if "jq" in run and "build" in run:
            order.setdefault("refuse", i)
    assert set(order) == {"checkout", "setup-bun", "install", "download", "refuse"}, order
    assert order["checkout"] < order["setup-bun"] < order["install"] < order["download"]
    assert order["download"] < order["refuse"] < token_index
    run = str(steps[token_index]["run"])
    assert "./node_modules/.bin/wrangler deploy" in run and "uses" not in steps[token_index]


def test_setup_bun_never_restores_from_the_actions_cache() -> None:
    """c6 LOW: the bun binary is downloaded, never restored from a shared cache."""
    setups = [
        (name, st)
        for name, job in _wf()["jobs"].items()
        for st in _steps(job)
        if _uses(st, "oven-sh/setup-bun")
    ]
    assert setups
    for name, st in setups:
        assert PINNED.match(st["uses"]), name
        assert st["with"].get("no-cache") is True, f"{name}: setup-bun without no-cache: true"


def test_no_secret_in_workflow_or_job_env() -> None:
    """c6 LOW: secrets reach steps that use them, never a whole job."""
    wf = _wf()
    assert "secrets." not in json.dumps(wf.get("env", {}))
    for name, job in wf["jobs"].items():
        assert "secrets." not in json.dumps(job.get("env", {})), f"{name}: secret in job-level env"


# ── Production only from main or a release tag ─────────────────────────────

_READY = {
    name: {"outputs": {"ready": "true", "api_url": "https://api.example.test", "artifact_id": "1"}}
    for name in ("gcp", "web-check", "web-build")
}


@pytest.mark.parametrize(
    ("event", "environment", "ref", "deploys"),
    [
        ("push", None, "refs/heads/main", True),  # staging
        ("push", None, "refs/tags/qcompass-v1.2.3", True),  # production from a release tag
        ("workflow_call", "production", "refs/heads/main", True),  # release-please
        ("workflow_dispatch", "production", "refs/heads/main", True),
        ("workflow_dispatch", "staging", "refs/heads/feature", True),
        ("workflow_dispatch", "production", "refs/heads/feature", False),
        ("workflow_dispatch", "production", "refs/tags/ucglef1-v1.0.0", False),
        ("workflow_dispatch", "production", "refs/pull/7/merge", False),
        ("workflow_call", "Production", "refs/heads/feature", False),  # case does not help
        ("workflow_call", "prod", "refs/heads/main", False),  # no such environment
    ],
)
def test_production_deploys_only_from_main_or_release_tags(
    event: str, environment: str | None, ref: str, deploys: bool
) -> None:
    ctx = {
        "inputs": {} if environment is None else {"environment": environment},
        "github": {"ref": ref, "event_name": event},
        "needs": _READY,
    }
    for name, job in _wf()["jobs"].items():
        runs = _truthy(_evaluate(str(job.get("if", "true")), ctx))
        assert runs is deploys, f"{name}: {event} {environment or '(default)'} on {ref}"
