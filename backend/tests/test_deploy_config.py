"""P3-07: container and deploy configuration is production-safe.

- Images (docker/Dockerfile.{cpu,cuda12}) run as a non-root user, pin
  Python 3.12 by exact patch, pin their bases by digest, declare a
  ``/healthz`` HEALTHCHECK in both the api and worker stages, carry OCI
  labels, default to ``QCOMPASS_ENV=production`` and never enable
  development-only anonymous access.
- Cloud Run services (deploy/*.yaml) take every secret from Secret Manager
  references, never set ``QCOMPASS_DEV_ALLOW_ANONYMOUS``, take
  ``QCOMPASS_ENV`` from the workflow (staging | production only) and probe
  ``/healthz``.
- The deploy workflow uses Part 6's secret names, reports
  ``BLOCKED-ON-JAMES`` when they are missing, and pins third-party actions
  by commit SHA.
- Dev anonymous access is impossible outside ``QCOMPASS_ENV=dev``.
- The worker's ``/healthz`` (what the probes call) tracks its loop.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
DOCKERFILES = [REPO / "docker" / "Dockerfile.cpu", REPO / "docker" / "Dockerfile.cuda12"]
SERVICES = sorted((REPO / "deploy").glob("*.yaml"))
DEPLOY_WORKFLOW = REPO / ".github" / "workflows" / "deploy.yml"
SECRET_NAMES = {"DATABASE_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}


def _stages(text: str) -> dict[str, str]:
    """Dockerfile body per ``FROM … AS <stage>``."""
    parts = re.split(r"^FROM\s+\S+(?:\s+AS\s+(\S+))?\s*$", text, flags=re.MULTILINE | re.IGNORECASE)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2) if parts[i]}


@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=lambda p: p.name)
def test_images_are_pinned_non_root_and_production(dockerfile: Path) -> None:
    text = dockerfile.read_text(encoding="utf-8")
    assert "QCOMPASS_DEV_ALLOW_ANONYMOUS" not in text.replace(
        "QCOMPASS_DEV_ALLOW_ANONYMOUS is not set",
        "",
    ), "images must never enable dev anonymous access"
    assert re.search(r"^\s+QCOMPASS_ENV=production", text, re.MULTILINE)
    assert re.search(r"^USER 10001:10001$", text, re.MULTILINE), "runtime must drop root"
    for arg in re.findall(r"^ARG (?:PYTHON|CUDA|UV)_IMAGE=(\S+)$", text, re.MULTILINE):
        assert "@sha256:" in arg, f"base image not pinned by digest: {arg}"
    assert re.search(
        r"(python:3\.12\.\d+-slim-bookworm@sha256|PYTHON_VERSION=3\.12\.\d+$)", text, re.MULTILINE
    )
    for label in ("title", "source", "version", "revision", "licenses"):
        assert f"org.opencontainers.image.{label}=" in text
    stages = _stages(text)
    assert {"api", "worker"} <= set(stages), stages.keys()
    for name in ("api", "worker"):
        assert re.search(r"HEALTHCHECK .*\n.*/healthz", stages[name]), (
            f"{name}: no /healthz HEALTHCHECK"
        )
    assert "qcompass_worker" in stages["worker"]
    assert "uv sync --frozen" in text, "dependencies must come from uv.lock"


@pytest.mark.parametrize("service", SERVICES, ids=lambda p: p.name)
def test_cloud_run_services_are_production_safe(service: Path) -> None:
    doc = yaml.safe_load(service.read_text(encoding="utf-8"))
    assert doc["apiVersion"] == "serving.knative.dev/v1" and doc["kind"] == "Service"
    spec = doc["spec"]["template"]["spec"]
    assert spec["serviceAccountName"] == "${GCP_SERVICE_ACCOUNT}"
    (container,) = spec["containers"]
    assert container["image"] == "${IMAGE}"
    env = {e["name"]: e for e in container["env"]}
    assert "QCOMPASS_DEV_ALLOW_ANONYMOUS" not in env
    assert env["QCOMPASS_ENV"]["value"] == "${QCOMPASS_ENV}"
    for name in SECRET_NAMES:
        ref = env[name]["valueFrom"]["secretKeyRef"]
        assert ref == {"name": name, "key": "latest"}, f"{name} must come from Secret Manager"
    for e in container["env"]:
        if "value" in e:
            assert e["value"].startswith("${") or e["name"] not in SECRET_NAMES
    for probe in ("startupProbe", "livenessProbe"):
        assert container[probe]["httpGet"] == {"path": "/healthz", "port": 8080}
    assert container["ports"] == [{"name": "http1", "containerPort": 8080}]


def test_worker_services_poll_with_cpu_always_allocated() -> None:
    for name, classes in (
        ("qcompass-worker-cpu", "cpu"),
        ("qcompass-worker-gpu", "gpu_small,gpu_large"),
    ):
        doc = yaml.safe_load((REPO / "deploy" / f"{name}.yaml").read_text(encoding="utf-8"))
        ann = doc["spec"]["template"]["metadata"]["annotations"]
        assert ann["run.googleapis.com/cpu-throttling"] == "false"
        assert doc["spec"]["template"]["spec"]["containers"][0]["args"] == ["--classes", classes]
        assert doc["metadata"]["annotations"]["run.googleapis.com/ingress"] == "internal"
    gpu = yaml.safe_load((REPO / "deploy" / "qcompass-worker-gpu.yaml").read_text(encoding="utf-8"))
    assert gpu["spec"]["template"]["spec"]["nodeSelector"] == {
        "run.googleapis.com/accelerator": "nvidia-l4"
    }


def test_deploy_workflow_checks_secrets_and_pins_actions() -> None:
    text = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    wf = yaml.safe_load(text)
    for name in (
        "GCP_PROJECT_ID",
        "GCP_REGION",
        "GCP_WORKLOAD_IDENTITY_PROVIDER",
        "GCP_SERVICE_ACCOUNT",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
    ):
        assert f"secrets.{name}" in text, f"{name} (PLAN Part 6) not read"
    assert text.count("BLOCKED-ON-JAMES:${list}") >= 3, "each check reports BLOCKED-ON-JAMES"
    assert "QCOMPASS_DEV_ALLOW_ANONYMOUS" not in text
    # QCOMPASS_ENV comes only from the target environment: staging | production.
    assert set(re.findall(r"'(staging|production|dev)'", text)) == {"staging", "production"}
    for job in ("gcp", "web"):
        assert "environment" in wf["jobs"][job]
    for uses in re.findall(r"uses:\s*(\S+)", text):
        owner = uses.split("/", 1)[0]
        if owner in {"actions", "oven-sh", "astral-sh"} or uses.startswith("./"):
            continue  # first-party / already used in ci.yml at these tags
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", uses), (
            f"third-party action not SHA-pinned: {uses}"
        )
    assert wf["jobs"]["gcp"]["permissions"]["id-token"] == "write"


@pytest.mark.parametrize("env", [None, "", "production", "staging", "prod", "DEV "])
def test_dev_anonymous_needs_qcompass_env_dev(
    monkeypatch: pytest.MonkeyPatch, env: str | None
) -> None:
    from ucgle_f1.m8_agent.principal import dev_anonymous_allowed

    monkeypatch.setenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", "1")
    if env is None:
        monkeypatch.delenv("QCOMPASS_ENV", raising=False)
    else:
        monkeypatch.setenv("QCOMPASS_ENV", env)
    expected = env is not None and env.strip().lower() == "dev"
    assert dev_anonymous_allowed() is expected


def test_worker_healthz_tracks_the_loop() -> None:
    from ucgle_f1.worker import Worker, serve_health

    class _NoQueue:  # healthz never touches the queue
        pass

    worker = Worker(_NoQueue(), ("cpu",), poll_seconds=0.1)  # type: ignore[arg-type]
    server = serve_health(worker, 0, host="127.0.0.1")
    url = f"http://127.0.0.1:{server.server_address[1]}/healthz"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = json.loads(resp.read())
        assert resp.status == 200 and body["status"] == "ok" and body["classes"] == ["cpu"]
        worker.last_loop = time.monotonic() - 3600  # loop stalled, no job running
        with pytest.raises(urllib.error.HTTPError) as stalled:
            urllib.request.urlopen(url, timeout=5)
        assert stalled.value.code == 503
        stalled.value.close()
        worker.busy = True  # a long job blocks the loop legitimately
        with urllib.request.urlopen(url, timeout=5) as resp:
            assert resp.status == 200
        worker.stop.set()
        with pytest.raises(urllib.error.HTTPError) as stopped:
            urllib.request.urlopen(url, timeout=5)
        assert stopped.value.code == 503
        stopped.value.close()
        with pytest.raises(urllib.error.HTTPError) as missing:
            urllib.request.urlopen(url.replace("/healthz", "/other"), timeout=5)
        assert missing.value.code == 404
        missing.value.close()
    finally:
        server.shutdown()
        server.server_close()
