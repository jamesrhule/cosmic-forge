"""PROMPT 1 v2 registry + suite runner tests."""

from __future__ import annotations

import pytest

from qcompass_bench import (
    FixtureManifest,
    Report,
    get_fixture,
    list_all_fixtures,
    reset_cache,
    run_benchmark_suite,
)


@pytest.fixture(autouse=True)
def _isolate() -> None:
    """Drop the in-process cache so each test starts fresh."""
    reset_cache()


def test_at_least_16_fixtures_across_at_least_6_domains() -> None:
    """PROMPT 1 v2 §DEFINITION OF DONE."""
    fixtures = list_all_fixtures()
    bundled = [f for f in fixtures if f.kind == "bundled_manifest"]
    assert len(bundled) >= 16, f"got {len(bundled)} bundled manifests"
    domains = {f.domain for f in bundled}
    assert {"cosmology", "chemistry", "condmat", "hep",
            "nuclear", "amo"}.issubset(domains)


def test_get_fixture_round_trips() -> None:
    fixture = get_fixture("kawai-kim-natural")
    assert isinstance(fixture, FixtureManifest)
    assert fixture.domain == "cosmology"
    assert fixture.qcompass_simulation == "cosmology.ucglef1"
    assert fixture.budget.metric == "eta_B"


def test_get_fixture_unknown_raises() -> None:
    with pytest.raises(KeyError, match="No fixture"):
        get_fixture("does-not-exist")


def test_run_benchmark_suite_returns_report_for_chemistry() -> None:
    pytest.importorskip("pyscf")
    report = run_benchmark_suite("chemistry", providers=["local_aer"])
    assert isinstance(report, Report)
    assert report.suite == "chemistry"
    assert report.providers == ["local_aer"]
    chem_records = [r for r in report.records if r.domain == "chemistry"]
    assert chem_records, "expected at least one chemistry record"
    h2 = [r for r in chem_records if r.fixture_id == "h2-sto3g"]
    assert h2, "h2-sto3g must run"
    assert h2[0].status in {"pass", "degraded"}, h2[0].notes
    # H2 STO-3G FCI tolerance is 1e-4 in the bundled manifest;
    # PySCF on a clean install converges below that.
    assert h2[0].status == "pass"
    # Provenance hash present.
    assert h2[0].classical_reference_hash


def test_run_benchmark_suite_all_grades_each_fixture() -> None:
    """`suite="all"` MUST return a record per bundled fixture × provider."""
    report = run_benchmark_suite("all", providers=["local_aer"])
    bundled_ids = {
        f.id for f in list_all_fixtures() if f.kind == "bundled_manifest"
    }
    record_ids = {r.fixture_id for r in report.records}
    assert bundled_ids == record_ids


def test_v2_fixture_manifest_round_trips() -> None:
    fixture = get_fixture("schwinger-1plus1d")
    blob = fixture.model_dump_json()
    restored = FixtureManifest.model_validate_json(blob)
    assert restored == fixture
