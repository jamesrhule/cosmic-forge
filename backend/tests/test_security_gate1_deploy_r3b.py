"""Gate 1 round 3B (OPS2): the deploy job deploys only the wrangler config the
build generates, and production only from the exact refs.

- MEDIUM, the round-3A refusal was a blocklist of three keys (build,
  containers, unsafe). A build-controlled dist/server/wrangler.json could
  still make wrangler read files of the deploy runner into the upload, among
  them /proc/self/environ with CLOUDFLARE_API_TOKEN in it, or bind the Worker
  to other resources of the account. Each case below plants one such config
  (or a symbolic link) in the build artifact and runs the token job's steps
  after the hand-over with the real locked wrangler (``--dry-run --outdir``):
  the token must never reach the upload, and the token step must not run.
- LOW, GitHub's ``==`` and ``startsWith`` ignore case, so the job-level guard
  let refs/heads/MAIN or refs/tags/QCOMPASS-V… deploy production. Each job's
  first step now checks the ref case-sensitively in bash.

The harness, the expression evaluator and the real build output come from
test_security_gate1_deploy.py (one shape per concern).
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from test_security_gate1_deploy import (
    _CLEAN,
    REPO,
    _evaluate,
    _resolve,
    _run_after_handover,
    _steps,
    _truthy,
    _wf,
)

SENTINEL = b"fake-CLOUDFLARE_API_TOKEN"
LEAK_MODULE = (
    'import leaked from "/proc/self/environ";\n'
    "export default { fetch() { return new Response(leaked); } };\n"
)

Plant = Callable[[Path], None] | None


def _cfg(**changes: Any) -> dict[str, Any]:
    config = copy.deepcopy(_CLEAN)
    for key, value in changes.items():
        if value is None:
            config.pop(key, None)
        else:
            config[key] = value
    return config


def _write(rel: str, text: str) -> Callable[[Path], None]:
    def plant(ws: Path) -> None:
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_text(text)

    return plant


def _symlink(rel: str, target: str) -> Callable[[Path], None]:
    def plant(ws: Path) -> None:
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).symlink_to(target)

    return plant


def _bypasses() -> dict[str, tuple[dict[str, Any] | str, Plant]]:
    esm = {"type": "ESModule", "globs": ["**/*.js", "**/*.mjs"]}
    assets = _CLEAN["assets"]
    with_proto = json.dumps(_CLEAN)[:-1] + (
        ', "__proto__": {"base_dir": "/proc/self", "find_additional_modules": true,'
        ' "rules": [{"type": "Text", "globs": ["environ"]}]}}'
    )
    escaped_key = json.dumps(_CLEAN)[:-1] + ', "\\u0073ite": {"bucket": "/proc/self"}}'
    return {
        # The round-3A verifier's repro (scratch-verify-OPS/exfil_sim.py).
        "bundling with a Text rule over /proc/self/environ": (
            _cfg(
                assets=None,
                no_bundle=False,
                rules=[*_CLEAN["rules"], {"type": "Text", "globs": ["**/environ"]}],
            ),
            _write("dist/server/index.js", LEAK_MODULE),
        ),
        "an extra rule with no_bundle kept": (
            _cfg(rules=[esm, {"type": "Text", "globs": ["**/*.txt"]}]),
            None,
        ),
        "base_dir and find_additional_modules": (
            _cfg(
                base_dir="/proc/self",
                find_additional_modules=True,
                rules=[esm, {"type": "Text", "globs": ["environ"]}],
            ),
            None,
        ),
        "text_blobs": (_cfg(text_blobs={"LEAK": "/proc/self/environ"}), None),
        "data_blobs": (_cfg(data_blobs={"LEAK": "/proc/self/environ"}), None),
        "wasm_modules": (_cfg(wasm_modules={"LEAK": "/proc/self/environ"}), None),
        "site.bucket": (_cfg(site={"bucket": "/proc/self"}), None),
        "assets.directory absolute": (_cfg(assets={**assets, "directory": "/proc/self"}), None),
        "assets.directory outside dist": (_cfg(assets={**assets, "directory": "../../.."}), None),
        "main outside dist/server": (_cfg(main="../../wrangler.jsonc"), None),
        "main absolute": (_cfg(main="/proc/self/environ"), None),
        "source maps naming a runner file": (
            _cfg(upload_source_maps=True),
            _write(
                "dist/server/index.js",
                "export default { fetch() { return new Response('ok') } }\n"
                "//# sourceMappingURL=/proc/self/environ\n",
            ),
        ),
        "an R2 binding": (_cfg(r2_buckets=[{"binding": "B", "bucket_name": "other"}]), None),
        "a KV binding": (_cfg(kv_namespaces=[{"binding": "K", "id": "0" * 32}]), None),
        "a D1 binding": (
            _cfg(d1_databases=[{"binding": "D", "database_name": "d", "database_id": "x"}]),
            None,
        ),
        "a service binding": (_cfg(services=[{"binding": "S", "service": "other-worker"}]), None),
        "a route on another zone": (
            _cfg(routes=[{"pattern": "example.com/*", "zone_name": "example.com"}]),
            None,
        ),
        "a var": (_cfg(vars={"QCOMPASS_ENV": "dev"}), None),
        "an environment section": (_cfg(env={"staging": {"vars": {"X": "y"}}}), None),
        "a key smuggled through __proto__": (with_proto, None),
        "a key spelled with a unicode escape": (escaped_key, None),
        "a symbolic link among the server modules": (
            _cfg(),
            _symlink("dist/server/assets/leak.js", "/proc/self/environ"),
        ),
        "a symbolic link among the public assets": (
            _cfg(),
            _symlink("dist/client/env.txt", "/proc/self/environ"),
        ),
        "a symbolic link for a directory": (
            _cfg(),
            _symlink("dist/server/assets", "/proc/self"),
        ),
    }


def _upload_holds_the_token(outdir: Path) -> list[str]:
    if not outdir.exists():
        return []
    return [
        str(p.relative_to(outdir))
        for p in outdir.rglob("*")
        if p.is_file() and not p.is_symlink() and SENTINEL in p.read_bytes()
    ]


@pytest.mark.parametrize("case", list(_bypasses()))
def test_m2_build_config_cannot_pull_runner_files_or_bindings_into_the_upload(
    tmp_path: Path, case: str
) -> None:
    assert (REPO / "node_modules" / ".bin" / "wrangler").exists(), "run `bun install` first"
    config, plant = _bypasses()[case]
    outdir = tmp_path / "upload"
    code, ran, token_step_ran, output = _run_after_handover(
        tmp_path, config, None, outdir=outdir, plant=plant
    )
    leaked = _upload_holds_the_token(outdir)
    assert not leaked, f"{case}: the Cloudflare token is in the upload: {leaked}"
    assert code != 0 and not token_step_ran, (
        f"{case}: wrangler ran with the token on this config (steps run: {ran}): {output[-400:]}"
    )


def test_m2_real_build_output_still_deploys_with_its_modules(tmp_path: Path) -> None:
    """Positive control: the real config, with module chunks and public
    assets as the build writes them, passes and wrangler uploads them."""
    assert (REPO / "node_modules" / ".bin" / "wrangler").exists(), "run `bun install` first"

    def plant(ws: Path) -> None:
        (ws / "dist/server/assets").mkdir(parents=True)
        (ws / "dist/server/assets/chunk-abc.js").write_text("export const x = 1;\n")
        (ws / "dist/server/index.js").write_text(
            'import { x } from "./assets/chunk-abc.js";\n'
            "export default { fetch() { return new Response(String(x)); } };\n"
        )
        (ws / "dist/server/.vite").mkdir()
        (ws / "dist/server/.vite/manifest.json").write_text("{}\n")
        (ws / "dist/client/.assetsignore").write_text("wrangler.json\n.dev.vars\n")

    outdir = tmp_path / "upload"
    code, ran, token_step_ran, output = _run_after_handover(
        tmp_path, _cfg(), None, outdir=outdir, plant=plant
    )
    assert code == 0 and token_step_ran, f"steps run: {ran}: {output[-800:]}"
    uploaded = {p.name for p in outdir.rglob("*") if p.is_file()}
    assert {"index.js", "chunk-abc.js"} <= uploaded, uploaded


def test_m2_allowlist_runs_from_the_checkout_after_the_download() -> None:
    wf = _wf()
    steps = _steps(wf["jobs"]["web"])
    names = [str(st.get("uses") or st.get("run")) for st in steps]
    download = next(i for i, n in enumerate(names) if n.startswith("actions/download-artifact@"))
    token = next(
        i for i, st in enumerate(steps) if "secrets.CLOUDFLARE_API_TOKEN" in json.dumps(st)
    )
    checks = [
        i
        for i, st in enumerate(steps)
        if str(st.get("run", "")).strip()
        == 'node scripts/check_wrangler_deploy_config.mjs "$WRANGLER_CONFIG"'
    ]
    assert len(checks) == 1, "one allowlist step, run from the checkout's scripts/"
    assert download < checks[0] < token
    assert all("uses" not in steps[i] for i in range(checks[0], token + 1))
    assert "if" not in steps[checks[0]], "the allowlist always runs"


# ── Production only from the exact refs ─────────────────────────────────────

_GUARD_NAME = "production only from main or a qcompass-v tag"
_READY = {
    name: {"outputs": {"ready": "true", "api_url": "https://api.example.test", "artifact_id": "1"}}
    for name in ("gcp", "web-check", "web-build")
}


def _first_step_refuses(job: dict[str, Any], target_env: str, ref: str, tmp_path: Path) -> bool:
    """Run the job's first step as the runner would; True if it fails the job."""
    first = _steps(job)[0]
    if "run" not in first or "if" in first:
        return False  # an action or a conditional step refuses nothing
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLOUDFLARE_", "GITHUB_"))}
    env.update(
        TARGET_ENV=target_env,
        GITHUB_REF=ref,
        GITHUB_OUTPUT=str(tmp_path / "output"),
        GITHUB_STEP_SUMMARY=str(tmp_path / "summary"),
    )
    env.update({k: _resolve(v) for k, v in (first.get("env") or {}).items()})
    proc = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", str(first["run"])],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return proc.returncode != 0


@pytest.mark.parametrize(
    ("event", "environment", "ref", "proceeds"),
    [
        ("push", None, "refs/heads/main", True),  # staging
        ("push", None, "refs/tags/qcompass-v1.2.3", True),  # production from a release tag
        ("workflow_call", "production", "refs/heads/main", True),  # release-please
        ("workflow_dispatch", "production", "refs/heads/main", True),
        ("workflow_dispatch", "staging", "refs/heads/Main", True),  # staging: any ref
        ("workflow_dispatch", "production", "refs/heads/MAIN", False),
        ("workflow_dispatch", "production", "refs/heads/Main", False),
        ("workflow_call", "production", "refs/heads/mAIN", False),
        ("push", None, "refs/tags/QCOMPASS-V9.9.9", False),  # the tag push itself
        ("workflow_dispatch", "production", "refs/tags/Qcompass-v1.0.0", False),
        ("workflow_dispatch", "Production", "refs/heads/MAIN", False),
        ("workflow_dispatch", "production", "refs/heads/feature", False),
    ],
)
def test_production_proceeds_only_from_exact_main_or_release_tag(
    tmp_path: Path, event: str, environment: str | None, ref: str, proceeds: bool
) -> None:
    wf = _wf()
    ctx = {
        "inputs": {} if environment is None else {"environment": environment},
        "github": {"ref": ref, "event_name": event},
        "needs": _READY,
    }
    target_env = str(_evaluate(str(wf["env"]["TARGET_ENV"]), ctx))
    for name, job in wf["jobs"].items():
        admitted = _truthy(_evaluate(str(job.get("if", "true")), ctx))
        runs = admitted and not _first_step_refuses(job, target_env, ref, tmp_path)
        assert runs is proceeds, f"{name}: {event} {environment or '(default)'} on {ref}"


def test_every_job_starts_with_the_same_unconditional_ref_check() -> None:
    jobs = _wf()["jobs"]
    firsts = {name: _steps(job)[0] for name, job in jobs.items()}
    for name, first in firsts.items():
        assert first.get("name") == _GUARD_NAME, f"{name}: the ref check is not the first step"
        assert "uses" not in first and "if" not in first and "env" not in first, name
    assert len({first["run"] for first in firsts.values()}) == 1, "one check, the same everywhere"


# ── SEC-L5 routing residual: per-environment GCP credentials ─────────────────


def test_gcp_credentials_come_from_the_target_environment() -> None:
    """The deployer, its WIF provider and the project are environment secrets
    of the job's GitHub environment, so staging and production can hold
    different service accounts (docs/qcompass/deployment.md) with no new
    secret name."""
    wf = _wf()
    gcp = wf["jobs"]["gcp"]
    assert gcp["environment"] == wf["env"]["TARGET_ENV"]
    text = json.dumps(gcp)
    for name in (
        "GCP_SERVICE_ACCOUNT",
        "GCP_WORKLOAD_IDENTITY_PROVIDER",
        "GCP_PROJECT_ID",
        "GCP_REGION",
    ):
        assert f"secrets.{name}" in text, name
    for other, job in wf["jobs"].items():
        if other != "gcp":
            assert "secrets.GCP_" not in json.dumps(job), f"{other} reads a GCP secret"


def test_m2_allowlist_mirrors_the_locked_plugin_with_the_same_wrangler() -> None:
    """The allowlist mirrors @cloudflare/vite-plugin 1.32.2's output step and
    reads wrangler.jsonc with the wrangler the plugin uses. A lock change to
    either fails here first: re-read the plugin's `outputConfigPlugin` and
    `readWorkerConfig`, update scripts/check_wrangler_deploy_config.mjs, and
    refresh backend/tests/data/wrangler_build_output.json from a build."""
    modules = REPO / "node_modules"
    plugin = json.loads((modules / "@cloudflare/vite-plugin/package.json").read_text())
    wrangler = json.loads((modules / "wrangler/package.json").read_text())
    assert plugin["version"] == "1.32.2"
    assert plugin["dependencies"]["wrangler"] == wrangler["version"] == "4.82.2"
    assert not (modules / "@cloudflare/vite-plugin/node_modules/wrangler").exists()
    source = (REPO / "scripts/check_wrangler_deploy_config.mjs").read_text()
    assert "@cloudflare/vite-plugin/dist/index.mjs (1.32.2" in source
