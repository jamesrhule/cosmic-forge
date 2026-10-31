"""External-benchmark adapters (PROMPT 1 v2).

Each module here lazy-imports a third-party benchmark library
(MQT-Bench, SupermarQ, QED-C App-Oriented Benchmarks) so the base
qcompass-bench install never depends on them. Adapters expose a
uniform :func:`run` surface that returns a list of
:class:`FixtureRunRecord` the registry's :class:`Report` can
absorb.
"""

from __future__ import annotations

from .mqt_bench import MQTBenchAdapter
from .qed_c import QedCAdapter
from .supermarq import SupermarQAdapter

__all__ = [
    "MQTBenchAdapter",
    "QedCAdapter",
    "SupermarQAdapter",
]
