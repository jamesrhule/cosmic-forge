"""FeMoco QPE template — dormant (PROMPT 9 v2 §D).

Emits a QIR placeholder + :class:`FaultTolerantPlan`. The
template is intentionally NOT executable on 2026 hardware —
calling :meth:`FemocoQPETemplate.execute` raises
``NotImplementedError``. Its purpose is to land the
resource-estimate envelope so the leaderboard + frontend can
display the projected wallclock / qubit budget alongside the
classical FCI / DMRG references.

The numbers come from the THC qubitised QPE construction (PRX
Quantum 2, 030305) refined by SCDF (arXiv:2403.03502). For the
canonical FeMoco active space (152 spin orbitals, ~6.3M Toffolis)
the closed-form Litinski estimate matches the Azure RE pin in
``qcompass_router.ft.test_vectors.PINNED_TEST_VECTORS`` within the
documented bracket.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qcompass_router.ft import FaultTolerantPlan, surface_code_compile


@dataclass(frozen=True)
class FemocoQPETemplate:
    """Inputs for the FeMoco QPE FT estimate.

    Defaults reproduce the active space + step count quoted in
    Lee et al. (2021). Override ``active_orbitals`` /
    ``toffoli_count`` to scan resource estimates.
    """

    active_orbitals: int = 152
    toffoli_count: int = 6_300_000
    qpe_bits: int = 28
    code_distance: int = 17
    qir_path: str | None = None
    notes: str = (
        "Dormant template per PROMPT 9 v2 §D. Emits QIR + "
        "FaultTolerantPlan only — execution on 2026 hardware "
        "raises NotImplementedError."
    )

    def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        msg = (
            "FemocoQPETemplate is dormant per PROMPT 9 v2 §D — "
            "the FT plan is the only deliverable on 2026 hardware. "
            "Re-baking against a fault-tolerant device requires the "
            "vendored QREChem + TFermion wheels at pinned SHAs."
        )
        raise NotImplementedError(msg)


@dataclass
class _FemocoCircuitShim:
    """Minimal duck-typed circuit object the FT estimator consumes."""

    num_qubits: int
    _ops: dict[str, int] = field(default_factory=dict)

    def count_ops(self) -> dict[str, int]:
        return dict(self._ops)


def emit_femoco_qpe_template(
    template: FemocoQPETemplate | None = None,
    *,
    qir_dir: Path | None = None,
) -> tuple[Path, FaultTolerantPlan]:
    """Emit the QIR placeholder + the FT plan for FeMoco QPE.

    Returns ``(qir_path, plan)``. The QIR module is a placeholder
    text artifact recording the template parameters; downstream
    consumers replace it with a real QIR emit when the
    Microsoft-Quantum QIR backend is wired.
    """
    template = template or FemocoQPETemplate()
    qir_dir = qir_dir or (Path.home() / ".qcompass" / "ft" / "femoco")
    qir_dir.mkdir(parents=True, exist_ok=True)
    qir_path = qir_dir / f"femoco_qpe_n{template.active_orbitals}.qir.txt"
    qir_path.write_text(_qir_placeholder(template))
    shim = _FemocoCircuitShim(
        num_qubits=template.active_orbitals,
        _ops={"ccx": template.toffoli_count // 7},
    )
    plan = surface_code_compile(
        shim,
        code_distance=template.code_distance,
        provider_hint="qrechem_femoco_template",
    )
    plan_with_qir = FaultTolerantPlan(
        logical_qubits=plan.logical_qubits,
        physical_qubits=plan.physical_qubits,
        wallclock_s=plan.wallclock_s,
        toffoli_count=template.toffoli_count,
        magic_state_factory=plan.magic_state_factory,
        code_distance=plan.code_distance,
        logical_error_rate=plan.logical_error_rate,
        qir_path=str(qir_path),
        provider="qrechem_femoco_template",
        notes=template.notes,
        breakdown={
            **plan.breakdown,
            "active_orbitals": template.active_orbitals,
            "qpe_bits": template.qpe_bits,
        },
    )
    return qir_path, plan_with_qir


def _qir_placeholder(template: FemocoQPETemplate) -> str:
    """Tiny QIR-text-format-flavoured placeholder."""
    return (
        "; QCompass FeMoco QPE template — PROMPT 9 v2 §D (dormant)\n"
        f"; active_orbitals = {template.active_orbitals}\n"
        f"; qpe_bits        = {template.qpe_bits}\n"
        f"; toffoli_count   = {template.toffoli_count}\n"
        f"; code_distance   = {template.code_distance}\n"
        "; references:\n"
        ";   PRX Quantum 2, 030305 (THC)\n"
        ";   arXiv:2403.03502 (SCDF)\n"
        "define void @femoco_qpe() {\n"
        "  ; ... Toffoli stack would land here when QIR backend is wired\n"
        "  ret void\n"
        "}\n"
    )


__all__ = ["FemocoQPETemplate", "emit_femoco_qpe_template"]
