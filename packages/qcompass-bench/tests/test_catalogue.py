"""S-bench-1: catalogue iterates exactly the registered domains."""

from __future__ import annotations

from qcompass_bench import list_all_fixtures, list_domain_names
from qcompass_core.registry import list_domains


def test_catalogue_matches_qcompass_core_registry() -> None:
    """qcompass-bench discovers domains via qcompass-core only."""
    bench_view = set(list_domain_names())
    core_view = set(list_domains())
    assert bench_view == core_view


def test_catalogue_skips_null_domain_for_fixtures() -> None:
    """The null plugin has no instances/ folder; gather should skip it."""
    fixtures = list_all_fixtures()
    assert all(f.domain != "null" for f in fixtures)


def test_chemistry_fixtures_present() -> None:
    fixtures = list_all_fixtures(domains=["chemistry"])
    names = {f.name for f in fixtures}
    # qfull-chemistry ships h2 / lih / n2 / femoco_toy.
    assert {"h2", "lih", "n2", "femoco_toy"}.issubset(names)
