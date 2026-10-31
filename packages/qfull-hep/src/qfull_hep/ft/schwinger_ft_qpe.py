"""Schwinger 3+1D FT template — dormant (PROMPT 9 v2 §E).

Particle-research extension: pairs the verified Schwinger 1+1D
real-time evolution with an FT estimate for the 3+1D scaling.
NOT executable on 2026 hardware — :meth:`SchwingerFTTemplate.execute`
raises ``NotImplementedError``. The plan is the deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qcompass_router.ft import FaultTolerantPlan, surface_code_compile


@dataclass(frozen=True)
class SchwingerFTTemplate:
    """Inputs for the Schwinger 3+1D QPE FT estimate.

    Defaults reproduce the Azure RE pin in
    :data:`qcompass_router.ft.test_vectors.PINNED_TEST_VECTORS`
    for the canonical N=128 scaling.
    """

    n_qubits: int = 128
    toffoli_count: int = 4_400_000
    qpe_bits: int = 24
    code_distance: int = 15
    notes: str = (
        "Dormant template per PROMPT 9 v2 §E. Emits QIR + "
        "FaultTolerantPlan only — execution on 2026 hardware "
        "raises NotImplementedError. Maps the 1+1D Schwinger "
        "kernel verified at L≤10 onto the FT 3+1D budget."
    )

    def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        msg = (
            "SchwingerFTTemplate is dormant per PROMPT 9 v2 §E — "
            "the FT plan is the only deliverable on 2026 hardware."
        )
        raise NotImplementedError(msg)


@dataclass
class _SchwingerCircuitShim:
    num_qubits: int
    _ops: dict[str, int] = field(default_factory=dict)

    def count_ops(self) -> dict[str, int]:
        return dict(self._ops)


def emit_schwinger_ft_qpe_template(
    template: SchwingerFTTemplate | None = None,
    *,
    qir_dir: Path | None = None,
) -> tuple[Path, FaultTolerantPlan]:
    """Emit the QIR placeholder + the FT plan for Schwinger 3+1D QPE."""
    template = template or SchwingerFTTemplate()
    qir_dir = qir_dir or (Path.home() / ".qcompass" / "ft" / "schwinger")
    qir_dir.mkdir(parents=True, exist_ok=True)
    qir_path = qir_dir / f"schwinger_ft_qpe_n{template.n_qubits}.qir.txt"
    qir_path.write_text(_qir_placeholder(template))
    shim = _SchwingerCircuitShim(
        num_qubits=template.n_qubits,
        _ops={"ccx": template.toffoli_count // 7},
    )
    plan = surface_code_compile(
        shim,
        code_distance=template.code_distance,
        provider_hint="hep_schwinger_ft_template",
    )
    return qir_path, FaultTolerantPlan(
        logical_qubits=plan.logical_qubits,
        physical_qubits=plan.physical_qubits,
        wallclock_s=plan.wallclock_s,
        toffoli_count=template.toffoli_count,
        magic_state_factory=plan.magic_state_factory,
        code_distance=plan.code_distance,
        logical_error_rate=plan.logical_error_rate,
        qir_path=str(qir_path),
        provider="hep_schwinger_ft_template",
        notes=template.notes,
        breakdown={
            **plan.breakdown,
            "qpe_bits": template.qpe_bits,
            "scaling_dim": "1+1D → 3+1D",
        },
    )


def _qir_placeholder(template: SchwingerFTTemplate) -> str:
    return (
        "; QCompass Schwinger 3+1D QPE template — PROMPT 9 v2 §E (dormant)\n"
        f"; n_qubits      = {template.n_qubits}\n"
        f"; qpe_bits      = {template.qpe_bits}\n"
        f"; toffoli_count = {template.toffoli_count}\n"
        f"; code_distance = {template.code_distance}\n"
        "; references:\n"
        ";   Farrell et al., PRX Quantum 5, 020315 (2024)\n"
        ";   Azure Quantum Resource Estimator pin (2024-09)\n"
        "define void @schwinger_ft_qpe() {\n"
        "  ; ... Toffoli stack lands here when QIR backend is wired\n"
        "  ret void\n"
        "}\n"
    )


__all__ = ["SchwingerFTTemplate", "emit_schwinger_ft_qpe_template"]
