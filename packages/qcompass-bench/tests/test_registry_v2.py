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


# ── PROMPT 3 v2 §"matching the fixtures registered in qcompass-bench" ──


def test_v2_plugin_bench_payload_alignment() -> None:
    """PROMPT 3 v2 reconciliation: each domain's plugin instances and
    bench bundled manifests overlap by payload (same physical content)
    even when filenames differ between snake_case and kebab-case.

    Pinning this invariant prevents future drift where a plugin's
    instances/ folder updates a fixture's payload but the bench's
    bundled manifest doesn't, or vice versa.
    """
    qfull_chem = pytest.importorskip("qfull_chem")
    qfull_cm = pytest.importorskip("qfull_cm")
    qfull_amo = pytest.importorskip("qfull_amo")

    # Chemistry — the bench bundles {h2-sto3g, lih-631g, n2-ccpvdz};
    # the plugin ships {h2, lih, n2, femoco_toy}. Pair the first
    # three by molecule + basis.
    chem_pairs = (
        ("h2-sto3g", "h2"),
        ("lih-631g", "lih"),
        ("n2-ccpvdz", "n2"),
    )
    for bench_id, plugin_id in chem_pairs:
        bench = get_fixture(bench_id)
        plugin = qfull_chem.load_instance(plugin_id)
        bench_problem = bench.payload_inline or {}
        assert bench_problem.get("molecule") == plugin.molecule, (
            f"{bench_id} vs {plugin_id}: molecule mismatch "
            f"({bench_problem.get('molecule')} vs {plugin.molecule})"
        )
        assert bench_problem.get("basis") == plugin.basis, (
            f"{bench_id} vs {plugin_id}: basis mismatch"
        )

    # Condmat — pair by problem kind + size descriptor.
    cm_pairs = (
        ("hubbard-4x4", "hubbard_4x4", "hubbard"),
        ("heisenberg-1d", "heisenberg_chain_10", "heisenberg"),
        ("otoc-loschmidt", "otoc_chain_8", "otoc"),
    )
    for bench_id, plugin_id, expected_kind in cm_pairs:
        bench = get_fixture(bench_id)
        plugin = qfull_cm.load_instance(plugin_id)
        assert plugin.kind == expected_kind, (
            f"{plugin_id}.kind={plugin.kind!r} != {expected_kind!r}"
        )
        bench_problem = bench.payload_inline or {}
        assert bench_problem.get("kind") == expected_kind, (
            f"{bench_id}.kind != {expected_kind}"
        )

    # AMO — pair MIS path-graph + Rydberg chain.
    amo_pairs = (
        ("rydberg-mis", "mis_path_5", "mis_toy"),
        ("rydberg-quench", "rydberg_chain_8", "rydberg_ground_state"),
    )
    for bench_id, plugin_id, expected_kind in amo_pairs:
        bench = get_fixture(bench_id)
        plugin = qfull_amo.load_instance(plugin_id)
        assert plugin.kind == expected_kind, (
            f"{plugin_id}.kind={plugin.kind!r} != {expected_kind!r}"
        )
        bench_problem = bench.payload_inline or {}
        assert bench_problem.get("kind") == expected_kind, (
            f"{bench_id}.kind != {expected_kind}"
        )
