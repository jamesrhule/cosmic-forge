"""Lovable handoff ↔ backend contract round-trip (PROMPT 11 §11.A).

Walks every JSON fixture Lovable shipped under
``public/fixtures/<domain>/runs/*.json`` and asserts:

  1. ``qcompass_core.Manifest.model_validate(blob['manifest'])``
     succeeds without dropping required fields.
  2. The reconstructed ``Manifest.problem`` is a SUPERSET of the
     fixture's ``problem`` block (the model may add default-valued
     keys but never drops ones the frontend ships).
  3. The fixture's ``provenance`` block populates the
     ``ProvenanceRecord`` shape without raising.
  4. The HEP fixtures (when present) carry the ``particle_obs``
     contract the ParticleObservablesTable consumes.
  5. The Nuclear fixtures (when present) carry a
     ``model_domain`` value the ModelDomainBadge recognises.

The chemistry fixtures are the ones Lovable's first run shipped;
the test grows automatically as the rest of the per-domain
``runs/`` dirs are populated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES_ROOT = _REPO_ROOT / "public" / "fixtures"


def _list_run_fixtures(domain: str) -> list[Path]:
    domain_root = _FIXTURES_ROOT / domain / "runs"
    if not domain_root.exists():
        return []
    return sorted(domain_root.glob("*.json"))


def _load_blob(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ── Chemistry ─────────────────────────────────────────────────────


CHEMISTRY_FIXTURES = _list_run_fixtures("chemistry")


@pytest.mark.parametrize(
    "fixture_path",
    CHEMISTRY_FIXTURES,
    ids=[p.stem for p in CHEMISTRY_FIXTURES] or ["_no_fixtures_"],
)
def test_chemistry_manifest_round_trips(fixture_path: Path) -> None:
    if not CHEMISTRY_FIXTURES:
        pytest.skip("No chemistry fixtures present")
    qcompass_core = pytest.importorskip("qcompass_core")
    blob = _load_blob(fixture_path)
    manifest = qcompass_core.Manifest.model_validate(blob["manifest"])

    assert manifest.domain == "chemistry"
    assert manifest.version == blob["manifest"]["version"]

    fixture_problem = blob["manifest"]["problem"]
    for key in fixture_problem:
        assert key in manifest.problem, (
            f"Pydantic Manifest dropped fixture problem key {key!r} "
            f"from {fixture_path.name}"
        )

    fixture_request = blob["manifest"]["backend_request"]
    request_dump = manifest.backend_request.model_dump(mode="json")
    for key, value in fixture_request.items():
        assert key in request_dump, (
            f"BackendRequest dropped fixture key {key!r} "
            f"from {fixture_path.name}"
        )
        # Value either matches verbatim or the model normalises None
        # / "auto" to the same default; flag mismatches so the
        # handoff-mismatches log can record them.
        if request_dump[key] != value and value is not None:
            pytest.fail(
                f"BackendRequest.{key} value mismatch in "
                f"{fixture_path.name}: fixture={value!r} "
                f"model={request_dump[key]!r}",
            )


@pytest.mark.parametrize(
    "fixture_path",
    CHEMISTRY_FIXTURES,
    ids=[p.stem for p in CHEMISTRY_FIXTURES] or ["_no_fixtures_"],
)
def test_chemistry_provenance_block_is_pydantic_compatible(
    fixture_path: Path,
) -> None:
    if not CHEMISTRY_FIXTURES:
        pytest.skip("No chemistry fixtures present")
    qcompass_core = pytest.importorskip("qcompass_core")
    blob = _load_blob(fixture_path)
    prov = blob.get("provenance")
    if prov is None:
        pytest.skip(f"{fixture_path.name} has no provenance block")
    rec = qcompass_core.ProvenanceRecord.model_validate(prov)
    assert rec.classical_reference_hash, (
        f"{fixture_path.name} provenance.classical_reference_hash empty"
    )


# ── HEP ───────────────────────────────────────────────────────────


HEP_FIXTURES = _list_run_fixtures("hep")


@pytest.mark.parametrize(
    "fixture_path",
    HEP_FIXTURES,
    ids=[p.stem for p in HEP_FIXTURES] or ["_no_fixtures_"],
)
def test_hep_runs_carry_particle_obs_block(fixture_path: Path) -> None:
    """When Lovable ships HEP run JSONs they MUST surface the
    ``particle_obs`` block (the ParticleObservablesTable contract).
    """
    if not HEP_FIXTURES:
        pytest.skip("No hep fixtures present")
    blob = _load_blob(fixture_path)
    obs = blob.get("particle_obs") or blob.get("metadata", {}).get(
        "particle_obs",
    )
    assert isinstance(obs, dict) and obs, (
        f"HEP run fixture {fixture_path.name} missing particle_obs"
    )
    for name, entry in obs.items():
        assert "value" in entry, f"{name}: value missing"
        assert "unit" in entry, f"{name}: unit missing"
        assert "status" in entry, f"{name}: status missing"


# ── Nuclear ──────────────────────────────────────────────────────


NUCLEAR_FIXTURES = _list_run_fixtures("nuclear")


@pytest.mark.parametrize(
    "fixture_path",
    NUCLEAR_FIXTURES,
    ids=[p.stem for p in NUCLEAR_FIXTURES] or ["_no_fixtures_"],
)
def test_nuclear_runs_carry_model_domain_tag(fixture_path: Path) -> None:
    if not NUCLEAR_FIXTURES:
        pytest.skip("No nuclear fixtures present")
    blob = _load_blob(fixture_path)
    md = (
        blob.get("model_domain")
        or blob.get("metadata", {}).get("model_domain")
        or blob.get("provenance", {})
        .get("error_mitigation_config", {})
        .get("model_domain")
    )
    assert md in {"1+1D_toy", "few_body_3d", "effective_hamiltonian"}, (
        f"Nuclear run fixture {fixture_path.name} model_domain "
        f"={md!r} (expected one of the canonical three)"
    )


# ── Gravity (provenance-warning gate) ─────────────────────────────


GRAVITY_FIXTURES = _list_run_fixtures("gravity")


@pytest.mark.parametrize(
    "fixture_path",
    GRAVITY_FIXTURES,
    ids=[p.stem for p in GRAVITY_FIXTURES] or ["_no_fixtures_"],
)
def test_gravity_learned_fixtures_carry_provenance_warning(
    fixture_path: Path,
) -> None:
    if not GRAVITY_FIXTURES:
        pytest.skip("No gravity fixtures present")
    blob = _load_blob(fixture_path)
    learned = bool(blob.get("is_learned_hamiltonian"))
    warning = blob.get("provenance_warning") or ""
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
    pytest.importorskip("qcompass_bench")
    text = yaml_path.read_text(encoding="utf-8")
    for needle in ("generated_at:", "cutoff_days:", "verdicts:", "status:"):
        assert needle in text, (
            f"sample-verdict.yaml missing canonical key {needle!r}"
        )
