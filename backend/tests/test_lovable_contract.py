"""Frontend fixture ↔ backend contract round-trip.

Walks every run fixture the workbench ships under
``public/fixtures/<domain>/runs/*.json`` and asserts that the backend's
wire models in ``qcompass_core.wire`` (mirrors of
``src/lib/domains/types.ts``) parse them without dropping a field:

  1. Every run fixture validates as ``DomainRunResult`` (``extra="forbid"``)
     and re-serialises to exactly the fixture's keys and values.
  2. Every fixture's ``provenance`` block is a ``ProvenanceRecordExt`` with a
     non-empty ``classical_reference_hash``.
  3. HEP fixtures carry the ``particle_obs`` block the
     ``ParticleObservablesTable`` consumes (label, value, uncertainty, units,
     provider, backend, calibration timestamp).
  4. Nuclear fixtures carry a ``model_domain`` the ``ModelDomainBadge``
     recognises, and it agrees with the provenance copy.
  5. Learned-Hamiltonian gravity fixtures carry a non-empty
     ``provenance_warning`` in their provenance block.
  6. The verdict sample validates as ``VerdictSample``.

Since P0-01 main's fixtures (``DomainRunResult`` shape) are the contract;
this file was corrected from the agent branch's manifest/energies envelope
(see ``docs/build/LEDGER.md`` → Corrected tests).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES_ROOT = _REPO_ROOT / "public" / "fixtures"


def _list_run_fixtures(domain: str | None = None) -> list[Path]:
    pattern = f"{domain}/runs/*.json" if domain else "*/runs/*.json"
    return sorted(_FIXTURES_ROOT.glob(pattern))


def _load_blob(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ids(paths: list[Path]) -> list[str]:
    return [f"{p.parent.parent.name}/{p.stem}" for p in paths] or ["_no_fixtures_"]


ALL_RUN_FIXTURES = _list_run_fixtures()


# ── Every domain ───────────────────────────────────────────────────


@pytest.mark.parametrize("fixture_path", ALL_RUN_FIXTURES, ids=_ids(ALL_RUN_FIXTURES))
def test_run_fixture_round_trips_as_domain_run_result(fixture_path: Path) -> None:
    if not ALL_RUN_FIXTURES:
        pytest.skip("No run fixtures present")
    wire = pytest.importorskip("qcompass_core.wire")
    blob = _load_blob(fixture_path)
    run = wire.DomainRunResult.model_validate(blob)

    assert run.id == fixture_path.stem
    dumped = run.model_dump(mode="json", exclude_unset=True)
    assert dumped == blob, (
        f"{fixture_path.name}: DomainRunResult dropped or altered fields: "
        f"missing={sorted(set(blob) - set(dumped))}"
    )


@pytest.mark.parametrize("fixture_path", ALL_RUN_FIXTURES, ids=_ids(ALL_RUN_FIXTURES))
def test_run_fixture_provenance_block_is_pydantic_compatible(fixture_path: Path) -> None:
    if not ALL_RUN_FIXTURES:
        pytest.skip("No run fixtures present")
    wire = pytest.importorskip("qcompass_core.wire")
    blob = _load_blob(fixture_path)
    prov = blob.get("provenance")
    assert prov is not None, f"{fixture_path.name} has no provenance block"
    rec = wire.ProvenanceRecordExt.model_validate(prov)
    assert rec.classical_reference_hash, (
        f"{fixture_path.name} provenance.classical_reference_hash empty"
    )


# ── HEP ───────────────────────────────────────────────────────────


HEP_FIXTURES = _list_run_fixtures("hep")


@pytest.mark.parametrize("fixture_path", HEP_FIXTURES, ids=_ids(HEP_FIXTURES))
def test_hep_runs_carry_particle_obs_block(fixture_path: Path) -> None:
    """HEP run JSONs MUST surface the ``particle_obs`` block (the
    ParticleObservablesTable contract)."""
    if not HEP_FIXTURES:
        pytest.skip("No hep fixtures present")
    blob = _load_blob(fixture_path)
    obs = blob.get("particle_obs")
    assert isinstance(obs, dict) and obs, (
        f"HEP run fixture {fixture_path.name} missing particle_obs"
    )
    for name, entry in obs.items():
        for key in ("label", "value", "uncertainty", "units", "provider", "backend", "calibration_at"):
            assert key in entry, f"{name}: {key} missing"
        assert isinstance(entry["value"], (int, float)), f"{name}: value not numeric"
        assert entry["uncertainty"] >= 0, f"{name}: negative uncertainty"


# ── Nuclear ──────────────────────────────────────────────────────


NUCLEAR_FIXTURES = _list_run_fixtures("nuclear")


@pytest.mark.parametrize("fixture_path", NUCLEAR_FIXTURES, ids=_ids(NUCLEAR_FIXTURES))
def test_nuclear_runs_carry_model_domain_tag(fixture_path: Path) -> None:
    if not NUCLEAR_FIXTURES:
        pytest.skip("No nuclear fixtures present")
    blob = _load_blob(fixture_path)
    md = blob.get("model_domain")
    assert md in {"1+1D_toy", "few_body_3d", "effective_hamiltonian"}, (
        f"Nuclear run fixture {fixture_path.name} model_domain "
        f"={md!r} (expected one of the canonical three)"
    )
    assert blob["provenance"].get("model_domain") == md, (
        f"{fixture_path.name}: provenance.model_domain disagrees with run.model_domain"
    )


# ── Gravity (provenance-warning gate) ─────────────────────────────


GRAVITY_FIXTURES = _list_run_fixtures("gravity")


@pytest.mark.parametrize("fixture_path", GRAVITY_FIXTURES, ids=_ids(GRAVITY_FIXTURES))
def test_gravity_learned_fixtures_carry_provenance_warning(fixture_path: Path) -> None:
    if not GRAVITY_FIXTURES:
        pytest.skip("No gravity fixtures present")
    blob = _load_blob(fixture_path)
    prov = blob["provenance"]
    learned = bool(blob.get("is_learned_hamiltonian")) or bool(prov.get("is_learned_hamiltonian"))
    assert bool(blob.get("is_learned_hamiltonian")) == bool(prov.get("is_learned_hamiltonian")), (
        f"{fixture_path.name}: run and provenance disagree on is_learned_hamiltonian"
    )
    warning = prov.get("provenance_warning") or ""
    if learned:
        assert warning.strip(), (
            f"Gravity learned-Hamiltonian fixture {fixture_path.name} "
            "MUST ship a non-empty provenance_warning."
        )


# ── Verdict samples ──────────────────────────────────────────────


VERDICT_DIR = _FIXTURES_ROOT / "verdict"


def test_verdict_sample_yaml_round_trips_when_present() -> None:
    yaml_path = VERDICT_DIR / "sample-verdict.yaml"
    if not yaml_path.exists():
        pytest.skip("No verdict sample fixture present")
    wire = pytest.importorskip("qcompass_core.wire")
    yaml = pytest.importorskip("yaml")
    sample = wire.VerdictSample.model_validate(yaml.safe_load(yaml_path.read_text(encoding="utf-8")))
    assert sample.rows, "sample-verdict.yaml has no rows"
    domains = [r.domain for r in sample.rows]
    assert len(domains) == len(set(domains)), "duplicate domain rows in verdict sample"
