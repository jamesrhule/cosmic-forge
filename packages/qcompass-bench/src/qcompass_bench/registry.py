"""Bundled-manifest registry + benchmark suite runner (PROMPT 1 v2).

Exposes the canonical v2 API:

  - :func:`list_all_fixtures` returns every bundled
    :class:`FixtureManifest` (the YAML files under
    ``qcompass_bench/manifests/<domain>/``) PLUS the per-plugin
    instances discovered via :mod:`qcompass_bench.catalogue`. Both
    are surfaced as ``FixtureManifest`` objects.
  - :func:`get_fixture` looks up a fixture by id.
  - :func:`run_benchmark_suite` executes a domain (or "all") through
    the bundled-manifest set on the requested provider list and
    returns a typed :class:`Report`.

The bundled-manifest set is the v2 source of truth; the
plugin-instance set is union-merged so existing tests (which look
for plugin fixtures by name) keep passing.
"""

from __future__ import annotations

import importlib.resources as resources
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml

from qcompass_core import BackendRequest, Manifest
from qcompass_core.registry import get_simulation, list_domains

from .schemas import FixtureManifest, NumericalBudget, SuiteDomain


# Ordered list of bundled-manifest packages. Adding a new domain
# = registering it here + creating a sibling subpackage with a
# `__init__.py` and YAML fixtures.
_DOMAIN_PACKAGES: tuple[tuple[SuiteDomain, str], ...] = (
    ("cosmology", "qcompass_bench.manifests.cosmology"),
    ("chemistry", "qcompass_bench.manifests.chemistry"),
    ("condmat",   "qcompass_bench.manifests.condmat"),
    ("hep",       "qcompass_bench.manifests.hep"),
    ("nuclear",   "qcompass_bench.manifests.nuclear"),
    ("amo",       "qcompass_bench.manifests.amo"),
)


def _load_bundled_manifests() -> list[FixtureManifest]:
    """Walk every domain package and load its YAML manifests."""
    out: list[FixtureManifest] = []
    for domain, package in _DOMAIN_PACKAGES:
        try:
            anchor = resources.files(package)
        except (ModuleNotFoundError, TypeError):
            continue
        for entry in sorted(anchor.iterdir(), key=lambda p: p.name):
            name = entry.name
            if not name.endswith(".yaml"):
                continue
            text = entry.read_text(encoding="utf-8")
            payload = yaml.safe_load(text)
            if not isinstance(payload, dict):
                msg = (
                    f"manifest at {package}/{name} must be a YAML "
                    "mapping; got "
                    f"{type(payload).__name__}"
                )
                raise ValueError(msg)
            payload.setdefault("domain", domain)
            out.append(FixtureManifest.model_validate(payload))
    return out


def _plugin_instance_manifests() -> list[FixtureManifest]:
    """Wrap every plugin's bundled YAML fixture as a FixtureManifest.

    Reuses the existing :mod:`qcompass_bench.catalogue` discovery so
    we don't duplicate the per-plugin walk. Any fixture id that
    overlaps with a bundled manifest's id is skipped here.
    """
    from .catalogue import list_all_fixtures as catalogue_list

    seen_ids = {m.id for m in _MANIFESTS_CACHE}
    out: list[FixtureManifest] = []
    for ref in catalogue_list():
        domain = _normalise_domain(ref.domain)
        if domain is None:
            continue
        # Catalogue refs use the YAML file's basename as ``name``;
        # the registry treats that as the id.
        fid = f"{domain}-{ref.name}"
        if fid in seen_ids:
            continue
        out.append(FixtureManifest(
            id=fid,
            name=f"{domain} / {ref.name} (plugin instance)",
            domain=domain,
            kind="plugin_instance",
            description=f"Per-plugin instance bundled in qfull-{domain}.",
            qcompass_simulation=ref.domain,
            payload_path=str(ref.path),
            payload_inline=None,
            budget=NumericalBudget(
                metric="finite_run",
                target="qualitative_pass",
                tolerance=None,
            ),
            references=[],
        ))
    return out


def _normalise_domain(name: str) -> SuiteDomain | None:
    if name == "cosmology.ucglef1":
        return "cosmology"
    if name in {"cosmology", "chemistry", "condmat", "hep",
                "nuclear", "amo", "gravity", "statmech"}:
        return name  # type: ignore[return-value]
    return None


_MANIFESTS_CACHE: list[FixtureManifest] = []


def _ensure_loaded() -> list[FixtureManifest]:
    if not _MANIFESTS_CACHE:
        _MANIFESTS_CACHE.extend(_load_bundled_manifests())
        _MANIFESTS_CACHE.extend(_plugin_instance_manifests())
    return _MANIFESTS_CACHE


def list_all_fixtures(
    *, domains: Iterable[str] | None = None,
) -> list[FixtureManifest]:
    """Return every known fixture (bundled + plugin-instance).

    The ``domains=`` filter is preserved for backwards compatibility
    with the existing test suite, which calls
    ``list_all_fixtures(domains=["chemistry"])``.
    """
    fixtures = _ensure_loaded()
    if domains is None:
        return list(fixtures)
    keep = set(domains)
    return [f for f in fixtures if f.domain in keep]


def get_fixture(id: str) -> FixtureManifest:
    """Look up a fixture by id."""
    for m in _ensure_loaded():
        if m.id == id:
            return m
    msg = f"No fixture with id={id!r}. Known: {[m.id for m in _ensure_loaded()]}"
    raise KeyError(msg)


def reset_cache() -> None:
    """Clear the in-process fixture cache (test-only)."""
    _MANIFESTS_CACHE.clear()


# ── Suite runner ──────────────────────────────────────────────────────


@dataclass
class FixtureRunRecord:
    """One bench fixture × provider record."""

    fixture_id: str
    domain: str
    provider: str
    status: str   # "pass" | "degraded" | "fail" | "skipped"
    primary_metric: str
    primary_value: float | str | None
    target: float | str
    tolerance: float | None
    wall_seconds: float
    classical_reference_hash: str
    notes: str = ""


@dataclass
class Report:
    """Output of :func:`run_benchmark_suite`."""

    suite: str
    providers: list[str]
    started_at: datetime
    records: list[FixtureRunRecord] = field(default_factory=list)

    def passed(self) -> int:
        return sum(1 for r in self.records if r.status == "pass")

    def total(self) -> int:
        return len(self.records)


_SUITE_ALIASES: dict[str, tuple[str, ...]] = {
    # PROMPT 5 v2 — fundamental-particle umbrella suite.
    "particle": ("hep", "nuclear"),
}


def run_benchmark_suite(
    suite: str,
    providers: list[str] | None = None,
) -> Report:
    """Execute every bundled fixture matching ``suite`` on each provider.

    ``suite`` accepts a domain (e.g. ``"cosmology"``), ``"all"``,
    or a v2 alias (currently ``"particle"`` → hep + nuclear).
    ``providers`` is currently informational — Phase-1 always runs
    on the local classical path; Phase-2 wires the qcompass-router
    so each provider yields its own record.
    """
    providers = list(providers or ["local_aer"])
    started = datetime.utcnow()

    if suite == "all":
        fixtures = list_all_fixtures()
    elif suite in _SUITE_ALIASES:
        fixtures = list_all_fixtures(domains=list(_SUITE_ALIASES[suite]))
    else:
        fixtures = list_all_fixtures(domains=[suite])
    fixtures = [f for f in fixtures if f.kind == "bundled_manifest"]

    records: list[FixtureRunRecord] = []
    for fixture in fixtures:
        for provider in providers:
            record = _run_fixture(fixture, provider)
            records.append(record)
    return Report(
        suite=suite,
        providers=providers,
        started_at=started,
        records=records,
    )


def _run_fixture(
    manifest: FixtureManifest,
    provider: str,
) -> FixtureRunRecord:
    """Drive a single bundled fixture through its qcompass plugin."""
    started = time.perf_counter()
    try:
        sim_cls = get_simulation(manifest.qcompass_simulation)
    except Exception as exc:
        return FixtureRunRecord(
            fixture_id=manifest.id,
            domain=manifest.domain,
            provider=provider,
            status="skipped",
            primary_metric=manifest.budget.metric,
            primary_value=None,
            target=manifest.budget.target,
            tolerance=manifest.budget.tolerance,
            wall_seconds=time.perf_counter() - started,
            classical_reference_hash="",
            notes=f"plugin lookup failed: {exc!s}",
        )

    payload = _resolve_payload(manifest)
    if payload is None:
        return FixtureRunRecord(
            fixture_id=manifest.id,
            domain=manifest.domain,
            provider=provider,
            status="skipped",
            primary_metric=manifest.budget.metric,
            primary_value=None,
            target=manifest.budget.target,
            tolerance=manifest.budget.tolerance,
            wall_seconds=time.perf_counter() - started,
            classical_reference_hash="",
            notes="payload could not be resolved",
        )

    backend_request = BackendRequest(kind="classical")
    qmanifest = Manifest(
        domain=manifest.domain if "." not in manifest.qcompass_simulation
        else manifest.domain,
        version="1.0",
        problem=payload,
        backend_request=backend_request,
    )
    try:
        sim = sim_cls()
        instance = sim.prepare(qmanifest)
        result = sim.run(instance, backend=None)  # type: ignore[arg-type]
    except Exception as exc:
        return FixtureRunRecord(
            fixture_id=manifest.id,
            domain=manifest.domain,
            provider=provider,
            status="fail",
            primary_metric=manifest.budget.metric,
            primary_value=None,
            target=manifest.budget.target,
            tolerance=manifest.budget.tolerance,
            wall_seconds=time.perf_counter() - started,
            classical_reference_hash="",
            notes=f"{type(exc).__name__}: {exc}",
        )

    primary_value = _extract_primary_metric(result, manifest.budget.metric)
    classical_hash = _extract_classical_hash(result)
    status = _grade(primary_value, manifest.budget)
    return FixtureRunRecord(
        fixture_id=manifest.id,
        domain=manifest.domain,
        provider=provider,
        status=status,
        primary_metric=manifest.budget.metric,
        primary_value=primary_value,
        target=manifest.budget.target,
        tolerance=manifest.budget.tolerance,
        wall_seconds=time.perf_counter() - started,
        classical_reference_hash=classical_hash,
        notes="",
    )


def _resolve_payload(manifest: FixtureManifest) -> dict[str, Any] | None:
    if manifest.payload_inline is not None:
        return dict(manifest.payload_inline)
    if manifest.payload_path is None:
        return None
    candidate = (
        Path(__file__).resolve().parent / "manifests" / manifest.domain
    ) / manifest.payload_path
    if not candidate.exists():
        # Try treating the path as relative to repo root.
        repo_candidate = Path(manifest.payload_path)
        if not repo_candidate.is_absolute():
            repo_candidate = (
                Path(__file__).resolve().parents[5] / manifest.payload_path
            )
        if repo_candidate.exists():
            candidate = repo_candidate
        else:
            return None
    if candidate.suffix == ".json":
        import json
        blob = json.loads(candidate.read_text())
        # cosmic-forge run fixtures wrap the manifest under ".config".
        return blob.get("config", blob)
    payload = yaml.safe_load(candidate.read_text())
    return payload if isinstance(payload, dict) else None


def _extract_primary_metric(result: Any, metric: str) -> float | None:
    direct = getattr(result, metric, None)
    if direct is not None:
        try:
            return float(direct)
        except (TypeError, ValueError):
            return None
    # Plugins surface energies under predictable attribute names.
    aliases = {
        "eta_B": ("eta_B",),
        "F_GB": ("F_GB",),
        "classical_energy": ("classical_energy",),
        "quantum_energy": ("quantum_energy",),
        "classical_energy_per_site": ("metadata", "classical", "energy_per_site"),
        "energy_per_atom": ("metadata", "classical", "energy_per_atom"),
        "chiral_condensate": ("metadata", "classical", "chiral_condensate"),
        "antisymmetry_residual": ("metadata", "classical", "antisymmetry_residual"),
        "otoc_magnitude": ("metadata", "classical", "otoc_magnitude"),
        "mis_size": ("metadata", "classical", "mis_size"),
    }
    chain = aliases.get(metric)
    if not chain:
        return None
    cur: Any = result
    for key in chain:
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            cur = getattr(cur, key, None)
        if cur is None:
            return None
    try:
        return float(cur)
    except (TypeError, ValueError):
        return None


def _extract_classical_hash(result: Any) -> str:
    for attr in ("classical_hash",):
        h = getattr(result, attr, None)
        if isinstance(h, str) and h:
            return h
    prov = getattr(result, "provenance", None)
    if prov is not None:
        h = getattr(prov, "classical_reference_hash", None)
        if isinstance(h, str) and h:
            return h
    return ""


def _grade(
    value: float | str | None, budget: NumericalBudget,
) -> str:
    if isinstance(budget.target, str):
        # Qualitative budget: any finite output → pass; missing →
        # degraded (the run completed without the metric).
        return "pass" if value is not None else "degraded"
    if value is None:
        return "fail"
    target = float(budget.target)
    tol = budget.tolerance
    if tol is None:
        return "pass"
    if budget.relative:
        if target == 0.0:
            ok = abs(value) <= tol
        else:
            ok = abs(value - target) / abs(target) <= tol
    else:
        ok = abs(value - target) <= tol
    return "pass" if ok else "degraded"
