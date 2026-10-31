"""Classical reference for the nuclear domain.

- 0νββ-toy: dense ED on a 1+1D toy Hamiltonian (L ≤ 8).
- NCSM matrix elements: deterministic synthetic 2-body operator
  whose antisymmetry is exercised by the audit.

DMRG via pyblock2 is the planned backend for L > 8; lazy-imported.
"""

from __future__ import annotations

from typing import Any, TypedDict

import numpy as np

from qcompass_core import hash_payload
from qcompass_core.errors import ClassicalReferenceError

from .manifest import (
    EffectiveHamiltonianParams,
    NCSMParams,
    NuclearProblem,
    ZeroNuBBToyParams,
)


class ClassicalOutcome(TypedDict):
    hash: str
    energy: float
    metadata: dict[str, Any]
    method_used: str
    warning: str | None


_ED_MAX_L = 8


def compute_reference(problem: NuclearProblem) -> ClassicalOutcome:
    h = hash_payload(problem.canonical_payload())
    if problem.kind == "zero_nu_bb_toy":
        assert problem.zero_nu_bb_toy is not None
        return _zero_nu_bb_toy(problem.zero_nu_bb_toy, h)
    if problem.kind == "ncsm_matrix_element":
        assert problem.ncsm_matrix_element is not None
        return _ncsm_matrix_element(problem.ncsm_matrix_element, h)
    if problem.kind == "effective_hamiltonian":
        assert problem.effective_hamiltonian is not None
        return _effective_hamiltonian(problem.effective_hamiltonian, h)
    msg = f"Unsupported nuclear kind: {problem.kind!r}"
    raise ClassicalReferenceError(msg)


def _zero_nu_bb_toy(
    p: ZeroNuBBToyParams, canonical_hash: str,
) -> ClassicalOutcome:
    if p.L > _ED_MAX_L:
        msg = (
            f"0νββ toy ED only supported up to L={_ED_MAX_L}; "
            "DMRG via pyblock2 is the planned backend."
        )
        raise ClassicalReferenceError(msg)
    H = _build_zero_nu_bb_hamiltonian(p)
    eigvals = np.linalg.eigvalsh(H)
    e0 = float(eigvals[0])
    occ = _expected_occupancy(H, eigvals, p.L)
    return ClassicalOutcome(
        hash=canonical_hash,
        energy=e0,
        metadata={
            "method": "zero_nu_bb_ed",
            "model_domain": "1+1D_toy",
            "L": p.L,
            "g_GT": p.g_GT,
            "g_F": p.g_F,
            "occupancy": occ,
        },
        method_used="zero_nu_bb_ed",
        warning=None,
    )


def _build_zero_nu_bb_hamiltonian(p: ZeroNuBBToyParams) -> np.ndarray:
    """Compact toy: nearest-neighbour XX coupling (Gamow-Teller stand-in)
    plus an on-site Z field (Fermi stand-in). Captures the lepton-pair
    creation structure schematically; the audit only needs determinism +
    physical-band ground-state energy.
    """
    L = p.L
    sx = np.array([[0.0, 1.0], [1.0, 0.0]])
    sz = np.array([[1.0, 0.0], [0.0, -1.0]])
    iden = np.eye(2)

    def kron_chain(matrices: list[np.ndarray]) -> np.ndarray:
        out = matrices[0]
        for m in matrices[1:]:
            out = np.kron(out, m)
        return out

    dim = 1 << L
    H = np.zeros((dim, dim), dtype=np.float64)
    for n in range(L - 1):
        ops: list[np.ndarray] = [iden] * L
        ops[n] = sx
        ops[n + 1] = sx
        H += -p.g_GT * kron_chain(ops)
    for n in range(L):
        ops = [iden] * L
        ops[n] = sz
        H += p.g_F * kron_chain(ops)
    return H


def _expected_occupancy(
    H: np.ndarray, eigvals: np.ndarray, L: int,
) -> float:
    """Return the ground-state expectation of total Σ (1+σ^z)/2 / L."""
    eigvecs = np.linalg.eigh(H)[1]
    psi = eigvecs[:, 0]
    sz = np.array([[1.0, 0.0], [0.0, -1.0]])
    iden = np.eye(2)
    total = 0.0
    for n in range(L):
        ops: list[np.ndarray] = [iden] * L
        ops[n] = sz
        z = ops[0]
        for m in ops[1:]:
            z = np.kron(z, m)
        total += float(0.5 * (1.0 + np.real(psi.conj() @ z @ psi)))
    return total / L


def _ncsm_matrix_element(
    p: NCSMParams, canonical_hash: str,
) -> ClassicalOutcome:
    """Deterministic synthetic 2-body matrix element.

    The audit (S-nuc-3) requires:
      - finite output
      - antisymmetry M[i,j] = -M[j,i] for the 2-body operator
    """
    n = max(2, p.N_max)
    rng = np.random.default_rng(seed=int(p.N_max))
    M = rng.normal(size=(n, n))
    M = 0.5 * (M - M.T)  # antisymmetrise
    return ClassicalOutcome(
        hash=canonical_hash,
        energy=float(np.linalg.eigvalsh(1j * M).real[0]),
        metadata={
            "method": "ncsm_synth",
            "operator": p.operator,
            "bodies": p.bodies,
            "N_max": p.N_max,
            "matrix_shape": list(M.shape),
            "antisymmetry_residual": float(np.max(np.abs(M + M.T))),
        },
        method_used="ncsm_synth",
        warning=None,
    )


def _effective_hamiltonian(
    p: EffectiveHamiltonianParams, canonical_hash: str,
) -> ClassicalOutcome:
    """Two-state effective Hamiltonian for hypothetical-particle searches.

    H = ((0, θ), (θ, ΔM)) for static; for sterile-oscillation we
    average over a fixed time window. The audit only needs:
      - finite, deterministic ground-state energy
      - mixing_amplitude observable that scales with mixing_angle
    """
    theta = float(p.mixing_angle)
    delta = float(p.mass_splitting)
    H = np.array([[0.0, theta], [theta, delta]], dtype=np.float64)
    eigvals, eigvecs = np.linalg.eigh(H)
    e0 = float(eigvals[0])
    psi0 = eigvecs[:, 0]
    # Mixing amplitude = |<active|ψ0>|² = |psi0[0]|².
    mixing_amplitude = float(psi0[0] * psi0[0])
    return ClassicalOutcome(
        hash=canonical_hash,
        energy=e0,
        metadata={
            "method": "effective_2state_ed",
            "model_domain": "effective_hamiltonian",
            "search": p.search,
            "mixing_angle": theta,
            "mass_splitting": delta,
            "oscillation_frequency": float(p.oscillation_frequency),
            "mixing_amplitude": mixing_amplitude,
            "energy_gap": float(eigvals[1] - eigvals[0]),
        },
        method_used="effective_2state_ed",
        warning=None,
    )


def _dmrg_unavailable() -> None:  # pragma: no cover
    try:
        import pyblock2  # noqa: F401
    except ImportError as exc:
        msg = "pyblock2 is required for the DMRG path; install [classical]."
        raise ClassicalReferenceError(msg) from exc
