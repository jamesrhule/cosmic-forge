"""Bench runner.

Iterates the requested catalogue + fixture set, runs each through
the plugin's ``Simulation.prepare/run/validate`` lifecycle on the
classical backend, and records a leaderboard row per fixture.

PROMPT 7's runner is intentionally classical-only — qcompass-bench
is a baseline harness, not a budget gate. The qcompass-router from
PROMPT 6 is the right place to dispatch quantum runs.
"""

from __future__ import annotations

import importlib
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

from qcompass_core import BackendRequest, Manifest
from qcompass_core.registry import get_simulation

from .catalogue import FixtureRef, list_all_fixtures, load_fixture
from .store import BenchEntry, LeaderboardStore


def run_bench(
    *,
    domains: list[str] | None = None,
    instance: str | None = None,
    store: LeaderboardStore | None = None,
    artifacts_root: Path | str | None = None,
) -> list[BenchEntry]:
    """Run the requested fixtures and append rows to the leaderboard."""
    fixtures = _select_fixtures(domains=domains, instance=instance)
    out_store = store or LeaderboardStore()
    rows: list[BenchEntry] = []
    for fixture in fixtures:
        entry = _run_fixture(fixture, artifacts_root=artifacts_root)
        out_store.record(entry)
        rows.append(entry)
    return rows


def _select_fixtures(
    *, domains: list[str] | None, instance: str | None,
) -> list[FixtureRef]:
    candidates = list_all_fixtures(domains=domains)
    if instance is None:
        return candidates
    return [f for f in candidates if f.name == instance]


def _run_fixture(
    fixture: FixtureRef,
    *,
    artifacts_root: Path | str | None = None,
) -> BenchEntry:
    sim_cls = get_simulation(fixture.domain)
    module_name = sim_cls.__module__.split(".")[0]
    module = importlib.import_module(module_name)
    package_version = str(getattr(module, "__version__", "unknown"))

    payload = load_fixture(fixture)
    manifest = Manifest(
        domain=_canonical_domain(fixture.domain),
        version="1.0",
        problem=payload,
        backend_request=BackendRequest(kind="classical"),
    )

    sim_kwargs: dict[str, object] = {}
    if artifacts_root is not None:
        sim_kwargs["artifacts_root"] = artifacts_root
    sim = sim_cls(**sim_kwargs)

    started = datetime.utcnow()
    t0 = time.perf_counter()
    ok = True
    notes = ""
    classical_energy: float | None = None
    quantum_energy: float | None = None
    provenance_hash = ""
    try:
        instance = sim.prepare(manifest)
        result = sim.run(instance, backend=None)  # type: ignore[arg-type]
        # Most plugins surface .classical_energy / .quantum_energy /
        # .classical_hash; fall back to .energy for the null plugin.
        classical_energy = _safe_float(getattr(result, "classical_energy", None))
        quantum_energy = _safe_float(getattr(result, "quantum_energy", None))
        if classical_energy is None and hasattr(result, "energy"):
            classical_energy = _safe_float(result.energy)
        provenance_hash = str(
            getattr(result, "classical_hash", None)
            or getattr(getattr(result, "provenance", None),
                       "classical_reference_hash", "")
            or ""
        )
    except Exception as exc:  # noqa: BLE001 — bench captures failures
        ok = False
        notes = f"{type(exc).__name__}: {exc}"
    wall = time.perf_counter() - t0
    return BenchEntry(
        domain=fixture.domain,
        fixture=fixture.name,
        package_version=package_version,
        started_at=started,
        wall_seconds=wall,
        classical_energy=classical_energy,
        quantum_energy=quantum_energy,
        provenance_hash=provenance_hash or "unavailable",
        ok=ok,
        notes=notes,
    )


def _canonical_domain(name: str) -> str:
    """Map plugin entry names to the qcompass-core DomainName literal.

    ``cosmology.ucglef1`` plugin reports ``domain="cosmology"`` in
    its manifest; the entry key is dotted.
    """
    if "." in name:
        return name.split(".")[0]
    return name


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f


def iter_runs(rows: Iterable[BenchEntry]) -> Iterable[BenchEntry]:
    """Convenience pass-through for callers that want to filter."""
    return rows
