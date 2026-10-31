"""FaultTolerantPlan dataclass (PROMPT 9 v2 §C).

Returned by :func:`surface_code_compile` and the per-domain FT
templates (FeMoco, Schwinger). Carries the wallclock /
qubit-count / Toffoli budget every leaderboard entry exposes
when the workflow targets a fault-tolerant device.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FaultTolerantPlan:
    """Resource estimate for a logical circuit on a surface-code FTQC.

    Field semantics mirror the Azure Quantum Resource Estimator
    output:

      logical_qubits — # of logical qubits the algorithm needs
      physical_qubits — # of physical qubits including code overhead
      wallclock_s — estimated total runtime at the target frequency
      toffoli_count — # of T / Toffoli gates the algorithm consumes
      magic_state_factory — vendor identifier for the factory pattern
                            ("ZX_15to1_d3" etc.)
      code_distance — surface-code distance d
      logical_error_rate — estimated end-to-end logical error rate
      qir_path — optional path to the emitted QIR module (for the
                 dormant FeMoco / Schwinger FT templates)
      provider — Azure RE / QREChem / TFermion / etc.
      notes — free-form vendor caveats
    """

    logical_qubits: int
    physical_qubits: int
    wallclock_s: float
    toffoli_count: int
    magic_state_factory: str
    code_distance: int = 7
    logical_error_rate: float = 1e-10
    qir_path: str | None = None
    provider: str = "azure_re"
    notes: str = ""
    breakdown: dict[str, Any] = field(default_factory=dict)

    def to_envelope(self) -> dict[str, Any]:
        """Serialise as the leaderboard / sidecar envelope."""
        return {
            "logical_qubits": self.logical_qubits,
            "physical_qubits": self.physical_qubits,
            "wallclock_s": self.wallclock_s,
            "toffoli_count": self.toffoli_count,
            "magic_state_factory": self.magic_state_factory,
            "code_distance": self.code_distance,
            "logical_error_rate": self.logical_error_rate,
            "qir_path": self.qir_path,
            "provider": self.provider,
            "notes": self.notes,
            "breakdown": dict(self.breakdown),
        }


__all__ = ["FaultTolerantPlan"]
