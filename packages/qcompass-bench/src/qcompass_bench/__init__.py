"""qcompass-bench — leaderboard harness."""

from __future__ import annotations

from .catalogue import (
    FixtureRef,
    list_all_fixtures,
    list_domain_names,
    list_fixtures,
    load_fixture,
)
from .report import render_markdown
from .runner import run_bench
from .store import BenchEntry, LeaderboardStore

__version__ = "0.1.0"

__all__ = [
    "BenchEntry",
    "FixtureRef",
    "LeaderboardStore",
    "list_all_fixtures",
    "list_domain_names",
    "list_fixtures",
    "load_fixture",
    "render_markdown",
    "run_bench",
]
