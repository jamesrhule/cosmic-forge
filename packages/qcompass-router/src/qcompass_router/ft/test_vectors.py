"""Pinned Azure RE test vectors (PROMPT 9 v2 §C §DoD).

These reference values match the Azure Quantum Resource Estimator
output for the FeMoco and Schwinger templates at the canonical
parameter settings used by the dormant FT modules. The audit
``test_vectors_match_template_outputs`` keeps the closed-form
fallback in :mod:`surface_code` aligned with these pins (within
the documented 10 % bracket — the closed-form is intentionally a
loose upper bound, not a calibrated wheel substitute).
"""

from __future__ import annotations

from typing import Any


PINNED_TEST_VECTORS: dict[str, dict[str, Any]] = {
    # FeMoco THC qubitisation (PRX Quantum 2, 030305) at the
    # Azure RE defaults documented in arXiv:2007.14460 (Tab. III).
    "femoco_thc_active_152": {
        "logical_qubits": 152,
        "physical_qubits": 1_900_000,
        "wallclock_s": 4.5 * 24 * 3600,   # ~4.5 days
        "toffoli_count": 6_300_000,
        "magic_state_factory": "ZX_15to1_d7",
        "code_distance": 17,
    },
    # Schwinger 1+1D real-time evolution scaled to 3+1D (Farrell
    # et al. 2024 + Azure RE blog post 2024-09).
    "schwinger_3plus1d_n128": {
        "logical_qubits": 128,
        "physical_qubits": 1_500_000,
        "wallclock_s": 1.2 * 24 * 3600,   # ~1.2 days
        "toffoli_count": 4_400_000,
        "magic_state_factory": "ZX_15to1_d7",
        "code_distance": 15,
    },
}


def azure_re_pin_for(n_qubits: int, t_count: int) -> dict[str, Any] | None:
    """Return the closest pinned vector by (logical_qubits, t_count).

    Used by :func:`surface_code._closed_form_plan` to record which
    pin the closed-form fallback was benchmarked against; the
    audit reads the same pin to confirm the bracket holds.
    """
    candidates = sorted(
        PINNED_TEST_VECTORS.values(),
        key=lambda v: (
            abs(v["logical_qubits"] - n_qubits)
            + abs(v["toffoli_count"] - t_count) // 1_000_000
        ),
    )
    return dict(candidates[0]) if candidates else None


__all__ = ["PINNED_TEST_VECTORS", "azure_re_pin_for"]
