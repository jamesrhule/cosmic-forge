"""PROMPT 5 v2 reconciliation tests.

Pin the v2 §DEFINITION OF DONE invariants:

  - ``list_domains()`` includes both ``hep`` and ``nuclear``.
  - ``run_benchmark_suite('particle', providers=['local_aer'])``
    returns one record per (HEP + nuclear) bundled fixture and
    each Schwinger record either passes or is degraded (never
    fail/skip when the classical kernel is on the path).
  - Every HEP / nuclear record carries the new ``particle_obs``
    schema fields (the bench surfaces them via the result the
    plugin returns; tested at the plugin layer here).
  - ``LatticeGaugeHamiltonian`` and ``NuclearShellHamiltonian``
    are exposed by ``qcompass_core.m11_hamiltonians`` and
    round-trip via ``model_validate`` / ``model_dump_json``.
"""

from __future__ import annotations

import pytest

from qcompass_bench import (
    list_all_fixtures,
    reset_cache,
    run_benchmark_suite,
)


@pytest.fixture(autouse=True)
def _isolate() -> None:
    reset_cache()


def test_list_domains_includes_hep_and_nuclear() -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    domains = set(qcompass_core.registry.list_domains())
    assert {"hep", "nuclear"}.issubset(domains)


def test_suite_particle_alias_picks_hep_plus_nuclear() -> None:
    pytest.importorskip("qfull_hep")
    pytest.importorskip("qfull_nuc")
    report = run_benchmark_suite("particle", providers=["local_aer"])
    assert report.suite == "particle"
    assert report.providers == ["local_aer"]

    domains = {r.domain for r in report.records}
    # Particle suite is {hep, nuclear} only.
    assert domains.issubset({"hep", "nuclear"})

    bundled = [
        f for f in list_all_fixtures(domains=["hep", "nuclear"])
        if f.kind == "bundled_manifest"
    ]
    record_ids = {r.fixture_id for r in report.records}
    assert {f.id for f in bundled} == record_ids


def test_suite_particle_schwinger_passes_on_classical_path() -> None:
    pytest.importorskip("qfull_hep")
    pytest.importorskip("qfull_nuc")
    report = run_benchmark_suite("particle", providers=["local_aer"])
    schwinger = [
        r for r in report.records
        if r.fixture_id.startswith("schwinger")
    ]
    assert schwinger, "expected a schwinger fixture in the particle suite"
    # Within 5% per v2 §DEFINITION OF DONE; pass or degraded both
    # acceptable since the bundled manifest's tolerance is the gate.
    for record in schwinger:
        assert record.status in {"pass", "degraded"}, (
            f"{record.fixture_id}: {record.notes}"
        )


def test_lattice_gauge_hamiltonian_round_trips() -> None:
    from qcompass_core.m11_hamiltonians import LatticeGaugeHamiltonian
    model = LatticeGaugeHamiltonian(
        gauge_group="U(1)",
        dimension=1,
        lattice_shape=(8, 16),
        fermion_encoding="kogut_susskind",
        mass=0.5,
        coupling=1.0,
        theta=0.0,
        n_flavors=1,
    )
    blob = model.model_dump_json()
    restored = LatticeGaugeHamiltonian.model_validate_json(blob)
    assert restored == model


def test_nuclear_shell_hamiltonian_round_trips() -> None:
    from qcompass_core.m11_hamiltonians import NuclearShellHamiltonian
    model = NuclearShellHamiltonian(
        n_single_particle=4,
        valence_space="p-shell",
        A=4,
        Z=2,
        two_body_inline=[[0.0, 1.0], [1.0, 0.0]],
    )
    blob = model.model_dump_json()
    restored = NuclearShellHamiltonian.model_validate_json(blob)
    assert restored == model


def test_nuclear_shell_rejects_Z_gt_A() -> None:
    from qcompass_core.m11_hamiltonians import NuclearShellHamiltonian
    with pytest.raises(ValueError, match="Z=.*cannot exceed A"):
        NuclearShellHamiltonian(
            n_single_particle=4,
            valence_space="p-shell",
            A=2,
            Z=3,
        )


def test_lattice_gauge_rejects_shape_dim_mismatch() -> None:
    from qcompass_core.m11_hamiltonians import LatticeGaugeHamiltonian
    with pytest.raises(ValueError, match="lattice_shape"):
        LatticeGaugeHamiltonian(
            gauge_group="SU(2)",
            dimension=2,
            lattice_shape=(4,),  # too few axes for dim=2
        )


def test_hep_classical_run_carries_particle_obs() -> None:
    qfull_hep = pytest.importorskip("qfull_hep")
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = qfull_hep.HEPSimulation()
    problem = qfull_hep.load_instance("schwinger_l4")
    manifest = qcompass_core.Manifest(
        domain="hep",
        version="1.0",
        problem=problem.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)

    assert "chiral_condensate" in result.particle_obs
    assert "string_tension" in result.particle_obs
    assert "anomaly_density" in result.particle_obs
    cond = result.particle_obs["chiral_condensate"]
    assert cond["unit"] == "dimensionless"
    assert cond["status"] == "ok"


def test_nuclear_effective_hamiltonian_search_paths() -> None:
    qfull_nuc = pytest.importorskip("qfull_nuc")
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = qfull_nuc.NuclearSimulation()
    for instance_name, expected_search in (
        ("heavy_neutrino_mixing", "heavy_neutrino_mixing"),
        ("sterile_neutrino_osc", "sterile_neutrino_oscillation"),
    ):
        problem = qfull_nuc.load_instance(instance_name)
        assert problem.kind == "effective_hamiltonian"
        assert problem.effective_hamiltonian is not None
        assert problem.effective_hamiltonian.search == expected_search
        assert problem.model_domain == "effective_hamiltonian"
        manifest = qcompass_core.Manifest(
            domain="nuclear",
            version="1.0",
            problem=problem.model_dump(),
            backend_request=qcompass_core.BackendRequest(kind="classical"),
        )
        ins = sim.prepare(manifest)
        backend = qcompass_core.get_backend(manifest.backend_request)
        result = sim.run(ins, backend)
        assert result.model_domain == "effective_hamiltonian"
        assert "mixing_amplitude" in result.particle_obs
