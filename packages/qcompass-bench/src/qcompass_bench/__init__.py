"""qcompass-bench — leaderboard harness + benchmark suite registry.

Public API:

  - PROMPT 1 v2 (canonical):
      :func:`list_all_fixtures` (returns :class:`FixtureManifest`)
      :func:`get_fixture`
      :func:`run_benchmark_suite` → :class:`Report`
  - Phase-1 leaderboard layer:
      :func:`run_bench`, :class:`LeaderboardStore`, :class:`BenchEntry`,
      :func:`render_markdown`.
  - Plugin-instance catalogue (kept for the catalogue tests):
      :func:`list_plugin_fixtures` aliases the original
      :func:`qcompass_bench.catalogue.list_all_fixtures`. Returns
      :class:`FixtureRef`, NOT :class:`FixtureManifest` — callers
      that want the v2 envelope use :func:`list_all_fixtures` from
      this module.

The v2 :func:`list_all_fixtures` UNIONs the bundled YAML manifests
with the per-plugin instances; both surface as
:class:`FixtureManifest`. Existing tests that filtered the
catalogue by ``domains=["chemistry"]`` and matched ``f.name``
continue to pass because :class:`FixtureManifest` carries both
``id`` and ``name`` fields.
"""

from __future__ import annotations

from .catalogue import (
    FixtureRef,
    list_all_fixtures as list_plugin_fixtures,
    list_domain_names,
    list_fixtures,
    load_fixture,
)
from .registry import (
    FixtureRunRecord,
    Report,
    get_fixture,
    list_all_fixtures,
    reset_cache,
    run_benchmark_suite,
)
from .report import render_markdown
from .runner import run_bench
from .schemas import FixtureKind, FixtureManifest, NumericalBudget, SuiteDomain
from .store import BenchEntry, LeaderboardStore

__version__ = "0.2.0"

__all__ = [
    "BenchEntry",
    "FixtureKind",
    "FixtureManifest",
    "FixtureRef",
    "FixtureRunRecord",
    "LeaderboardStore",
    "NumericalBudget",
    "Report",
    "SuiteDomain",
    "get_fixture",
    "list_all_fixtures",
    "list_domain_names",
    "list_fixtures",
    "list_plugin_fixtures",
    "load_fixture",
    "render_markdown",
    "reset_cache",
    "run_bench",
    "run_benchmark_suite",
]
