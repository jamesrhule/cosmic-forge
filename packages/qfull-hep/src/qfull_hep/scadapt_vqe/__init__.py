"""SC-ADAPT-VQE — Schwinger model adaptive VQE wrapper.

PROMPT 5 §B asks us to "vendor the minimal Python version under
``src/qfull_hep/scadapt_vqe/``" to enable Schwinger-model SC-ADAPT-VQE
runs (Farrell et al., arXiv:2401.04188 / IQuS).

The Phase-1 implementation ships a **stub module** that documents
the upstream reference and lazy-imports any candidate ``scadapt_vqe``
package the user has installed locally. Vendoring the actual code
needs a license review (research IP) and lands behind a
``physics-reviewed`` PR label in a follow-up.

Until then, calling :func:`run_scadapt_vqe` raises a clear
:class:`NotImplementedError` so the caller can degrade gracefully
to the classical or IBM digital path.
"""

from __future__ import annotations

from typing import Any

from ..classical import compute_reference
from ..manifest import HEPProblem


VENDOR_REFERENCE = "arXiv:2401.04188 — Farrell et al. 2024 (IQuS SC-ADAPT-VQE)"


def is_available() -> bool:
    """Return True iff a Python module named ``scadapt_vqe`` is importable."""
    try:
        import scadapt_vqe  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False
    return True


def run_scadapt_vqe(problem: HEPProblem) -> dict[str, Any]:
    """Run the Schwinger SC-ADAPT-VQE schedule.

    Phase-1 stub: raises ``NotImplementedError``. The classical
    reference is still computed so the dispatcher can record the
    provenance hash even when this path isn't reached.
    """
    if not is_available():
        msg = (
            "scadapt_vqe is not vendored yet. See "
            f"{VENDOR_REFERENCE}; vendoring requires a physics-reviewed PR."
        )
        raise NotImplementedError(msg)

    # If a future PR vendors the package, the call site lands here.
    msg = (
        "scadapt_vqe is importable but the qfull-hep adapter still "
        "needs Phase-2 wiring."
    )
    raise NotImplementedError(msg)


def classical_pairing(problem: HEPProblem) -> dict[str, Any]:
    """Convenience: every SC-ADAPT-VQE call must record a classical hash."""
    outcome = compute_reference(problem)
    return {
        "hash": outcome["hash"],
        "energy": outcome["energy"],
        "method_used": outcome["method_used"],
        "warning": outcome["warning"],
    }
