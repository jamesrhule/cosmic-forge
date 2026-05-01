"""S-bench-1: catalogue iterates exactly the registered domains.

PROMPT 1 v2 added a bundled-manifest registry whose
``list_all_fixtures`` returns :class:`FixtureManifest`. The
plugin-instance catalogue from PROMPT 7 v1 is preserved as
``list_plugin_fixtures`` for the original tests below.
"""

from __future__ import annotations

from qcompass_bench import (
    list_all_fixtures,
    list_domain_names,
    list_plugin_fixtures,
)
from qcompass_core.registry import list_domains


def test_catalogue_matches_qcompass_core_registry() -> None:
    """qcompass-bench discovers domains via qcompass-core only."""
    bench_view = set(list_domain_names())
    core_view = set(list_domains())
    assert bench_view == core_view


def test_catalogue_skips_null_domain_for_fixtures() -> None:
    """The null plugin has no instances/ folder; gather should skip it."""
    fixtures = list_plugin_fixtures()
    assert all(f.domain != "null" for f in fixtures)


def test_chemistry_plugin_fixtures_present() -> None:
    fixtures = list_plugin_fixtures(domains=["chemistry"])
    names = {f.name for f in fixtures}
    # qfull-chemistry ships h2 / lih / n2 / femoco_toy.
    assert {"h2", "lih", "n2", "femoco_toy"}.issubset(names)


def test_v2_list_all_fixtures_returns_manifest_objects() -> None:
    """v2 API returns FixtureManifest with `.id`, `.domain`, `.budget`."""
    from qcompass_bench import FixtureManifest

    fixtures = list_all_fixtures()
    assert all(isinstance(f, FixtureManifest) for f in fixtures)
    assert len(fixtures) >= 16
    domains = {f.domain for f in fixtures if f.kind == "bundled_manifest"}
    assert {"cosmology", "chemistry", "condmat", "hep",
            "nuclear", "amo"}.issubset(domains)


def test_v2_chemistry_bundled_manifests() -> None:
    """The 3 bundled chemistry manifests are addressable by id."""
    from qcompass_bench import get_fixture

    for fid in ("h2-sto3g", "lih-631g", "n2-ccpvdz"):
        fixture = get_fixture(fid)
        assert fixture.domain == "chemistry"
        assert fixture.kind == "bundled_manifest"
        assert fixture.budget.metric
