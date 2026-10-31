"""QCompass meta-package (PROMPT 10 v2 §E).

Re-exports the canonical entry points so application code can write::

    from qcompass import list_domains, Manifest, BackendRequest

without remembering whether the symbol lives in qcompass-core,
qcompass-router, or qcompass-bench. Heavy domain plugins
(qfull-*) keep their own import paths.
"""

from __future__ import annotations

# Core protocol layer.
from qcompass_core import (
    BackendRequest,
    Manifest,
    Simulation,
    emit_provenance,
    hash_payload,
)
from qcompass_core.registry import (
    get_simulation,
    list_domains,
    register,
)

# Router surface.
from qcompass_router import (
    Cost,
    PricingEngine,
    Router,
    RouterRequest,
    RoutingDecision,
)

# Bench surface.
from qcompass_bench import (
    FixtureManifest,
    Report,
    VerdictReport,
    list_all_fixtures,
    run_benchmark_suite,
    run_verdict,
)

__version__ = "0.1.0"

__all__ = [
    "BackendRequest",
    "Cost",
    "FixtureManifest",
    "Manifest",
    "PricingEngine",
    "Report",
    "Router",
    "RouterRequest",
    "RoutingDecision",
    "Simulation",
    "VerdictReport",
    "emit_provenance",
    "get_simulation",
    "hash_payload",
    "list_all_fixtures",
    "list_domains",
    "register",
    "run_benchmark_suite",
    "run_verdict",
]
