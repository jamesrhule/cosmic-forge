"""qcompass_router.ft — fault-tolerant resource estimation (PROMPT 9 v2 §C).

Public surface:

  - :class:`FaultTolerantPlan`   — vendor-neutral plan envelope.
  - :func:`surface_code_compile` — compile a logical circuit to a
    surface-code FT plan via Azure RE / QREChem / TFermion (soft-
    imported) with a closed-form Litinski fallback.
  - :data:`PINNED_TEST_VECTORS`  — canonical Azure RE outputs for
    the FeMoco + Schwinger templates the v2 §DoD pins.

Heavy deps (azure-quantum, QREChem, TFermion) are SOFT-IMPORTED
so the package stays importable in environments that only need
the closed-form path or the dataclass.
"""

from __future__ import annotations

from .plan import FaultTolerantPlan
from .surface_code import surface_code_compile
from .test_vectors import PINNED_TEST_VECTORS, azure_re_pin_for

__all__ = [
    "FaultTolerantPlan",
    "PINNED_TEST_VECTORS",
    "azure_re_pin_for",
    "surface_code_compile",
]
