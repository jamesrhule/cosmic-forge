"""Classical references (scipy MC) for the statmech kernels.

- ``qae``: classical Monte-Carlo estimate of the same integrand
  the quantum amplitude estimation targets.
- ``metropolis_ising``: dense ED of the transverse-field Ising
  chain to compute the Boltzmann partition function and ⟨E⟩ at
  inverse temperature β.
- ``tfd``: same Ising backbone, returns the partition function
  derived from the eigenvalues so the TFD-prep audit can compare.
"""

from __future__ import annotations

from typing import Any, TypedDict

import numpy as np

from qcompass_core import hash_payload
from qcompass_core.errors import ClassicalReferenceError

from .manifest import (
    IsingMetropolisParams,
    QAEParams,
    StatmechProblem,
    TFDParams,
)


class ClassicalOutcome(TypedDict):
    hash: str
    energy: float
    metadata: dict[str, Any]
    method_used: str
    warning: str | None


def compute_reference(problem: StatmechProblem) -> ClassicalOutcome:
    h = hash_payload(problem.canonical_payload())
    if problem.kind == "qae":
        assert problem.qae is not None
        return _qae_classical_mc(problem.qae, h, seed=problem.seed)
    if problem.kind == "metropolis_ising":
        assert problem.metropolis_ising is not None
        return _ising_partition(problem.metropolis_ising, h)
    if problem.kind == "tfd":
        assert problem.tfd is not None
        return _tfd_partition(problem.tfd, h)
    msg = f"Unsupported statmech kind: {problem.kind!r}"
    raise ClassicalReferenceError(msg)


# ── QAE classical reference ────────────────────────────────────────


def _qae_classical_mc(
    p: QAEParams, canonical_hash: str, *, seed: int = 0,
) -> ClassicalOutcome:
    rng = np.random.default_rng(seed)
    n = p.n_samples
    if p.integrand == "bell":
        # Closed form: P(coin == 1) for a fair coin = 0.5.
        samples = rng.uniform(0.0, 1.0, size=n) < p.truth
    elif p.integrand == "gaussian":
        # ∫ N(0,1)(x) over (−∞, x*] truncated to x* such that Φ(x*) = truth.
        from scipy.stats import norm
        x_star = float(norm.ppf(p.truth))
        samples = rng.standard_normal(size=n) <= x_star
    elif p.integrand == "indicator":
        # P[U(0,1) <= truth] = truth.
        samples = rng.uniform(0.0, 1.0, size=n) <= p.truth
    else:
        msg = f"unknown QAE integrand: {p.integrand!r}"
        raise ClassicalReferenceError(msg)
    estimate = float(np.mean(samples))
    sigma = float(np.std(samples, ddof=1) / np.sqrt(n))
    return ClassicalOutcome(
        hash=canonical_hash,
        # "Energy" placeholder so the surrounding result envelope keeps
        # the same shape as other domains; QAE-specific value lives
        # under metadata.
        energy=estimate,
        metadata={
            "method": "scipy_mc_qae",
            "model_domain": "stat_mech_mc",
            "integrand": p.integrand,
            "estimate": estimate,
            "sigma": sigma,
            "truth": p.truth,
            "n_samples": n,
            "abs_error": abs(estimate - p.truth),
        },
        method_used="scipy_mc_qae",
        warning=None,
    )


# ── Ising helpers ──────────────────────────────────────────────────


def _build_ising_h(L: int, J: float, h: float) -> np.ndarray:
    """Transverse-field Ising chain: H = -J Σ Z_i Z_{i+1} - h Σ X_i."""
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
        ops_z: list[np.ndarray] = [iden] * L
        ops_z[n] = sz
        ops_z[n + 1] = sz
        H -= J * kron_chain(ops_z)
    for n in range(L):
        ops_x: list[np.ndarray] = [iden] * L
        ops_x[n] = sx
        H -= h * kron_chain(ops_x)
    return H


def _ising_partition(
    p: IsingMetropolisParams, canonical_hash: str,
) -> ClassicalOutcome:
    H = _build_ising_h(p.L, p.J, p.h)
    eigvals = np.linalg.eigvalsh(H)
    # Z(β) = sum_i exp(-β E_i); ⟨E⟩ = sum_i E_i exp(-β E_i) / Z(β).
    weights = np.exp(-p.beta * (eigvals - eigvals[0]))
    Z = float(np.sum(weights)) * np.exp(-p.beta * eigvals[0])
    mean_E = float(np.sum(eigvals * weights) / np.sum(weights))
    return ClassicalOutcome(
        hash=canonical_hash,
        energy=mean_E,
        metadata={
            "method": "ising_partition_ed",
            "model_domain": "stat_mech_ising",
            "L": p.L,
            "beta": p.beta,
            "Z": Z,
            "ground_state": float(eigvals[0]),
            "mean_energy": mean_E,
        },
        method_used="ising_partition_ed",
        warning=None,
    )


def _tfd_partition(p: TFDParams, canonical_hash: str) -> ClassicalOutcome:
    """For the TFD audit we just need Z(β) on the same chain backbone."""
    H = _build_ising_h(p.L, p.J, 0.5)
    eigvals = np.linalg.eigvalsh(H)
    weights = np.exp(-p.beta * (eigvals - eigvals[0]))
    Z = float(np.sum(weights)) * np.exp(-p.beta * eigvals[0])
    return ClassicalOutcome(
        hash=canonical_hash,
        energy=float(eigvals[0]),
        metadata={
            "method": "tfd_partition_ed",
            "model_domain": "stat_mech_tfd",
            "L": p.L, "beta": p.beta,
            "Z": Z,
            "ground_state": float(eigvals[0]),
        },
        method_used="tfd_partition_ed",
        warning=None,
    )
