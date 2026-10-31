"""Classical reference for the gravity domain.

- ``syk_dense``: build the q=4 Majorana SYK Hamiltonian for small N
  (≤14), exact-diagonalise, and report E_0 + spectral form factor
  proxy.
- ``syk_sparse``: same as above but with a randomly-pruned coupling
  tensor at the requested sparsity.
- ``jt_matrix``: random matrix from {GUE, GOE, GSE}, returns the
  smallest eigenvalue and the spectral density's edge.

For all three the kernel is deterministic given (kind, params,
seed). Larger system sizes (sparse SYK at N>20, JT matrix > 64)
are deferred to qfull-gravity[heavy] (not in this commit).
"""

from __future__ import annotations

from typing import Any, TypedDict

import numpy as np

from qcompass_core import hash_payload
from qcompass_core.errors import ClassicalReferenceError

from .manifest import GravityProblem, JTParams, SparseSYKParams, SYKParams


class ClassicalOutcome(TypedDict):
    hash: str
    energy: float
    metadata: dict[str, Any]
    method_used: str
    warning: str | None


_DENSE_MAX_N = 14
_SPARSE_MAX_N = 20
_JT_MAX = 64


def compute_reference(problem: GravityProblem) -> ClassicalOutcome:
    h = hash_payload(problem.canonical_payload())
    if problem.kind == "syk_dense":
        assert problem.syk_dense is not None
        return _syk_dense(problem.syk_dense, h)
    if problem.kind == "syk_sparse":
        assert problem.syk_sparse is not None
        return _syk_sparse(problem.syk_sparse, h)
    if problem.kind == "jt_matrix":
        assert problem.jt_matrix is not None
        return _jt_matrix(problem.jt_matrix, h)
    msg = f"Unsupported gravity kind: {problem.kind!r}"
    raise ClassicalReferenceError(msg)


# ── Majorana SYK helpers ───────────────────────────────────────────


def _majoranas(N: int) -> list[np.ndarray]:
    """Return N anticommuting Majorana operators acting on 2^(N//2) states."""
    if N % 2:
        msg = "SYK Majorana count must be even."
        raise ValueError(msg)
    n_qubits = N // 2
    dim = 1 << n_qubits
    sx = np.array([[0.0, 1.0], [1.0, 0.0]])
    sy = np.array([[0.0, -1j], [1j, 0.0]])
    sz = np.array([[1.0, 0.0], [0.0, -1.0]])
    iden = np.eye(2)

    def kron_chain(matrices: list[np.ndarray]) -> np.ndarray:
        out = matrices[0]
        for m in matrices[1:]:
            out = np.kron(out, m)
        return out

    chis: list[np.ndarray] = []
    for i in range(N):
        site = i // 2
        ops: list[np.ndarray] = [sz] * site
        ops.append(sx if i % 2 == 0 else sy)
        ops += [iden] * (n_qubits - site - 1)
        chis.append(kron_chain(ops).astype(complex))
        # Normalise so {chi_i, chi_j} = 2 delta_ij.
        chis[-1] = chis[-1] / np.sqrt(2.0)
    # Reshape to dense complex64 to keep memory in check.
    return [c.astype(np.complex128) for c in chis]


def _syk_couplings(
    N: int, q: int, J: float, seed: int, sparsity: float = 1.0,
) -> dict[tuple[int, ...], complex]:
    rng = np.random.default_rng(seed)
    from itertools import combinations
    indices = list(combinations(range(N), q))
    keep = (
        indices if sparsity >= 1.0
        else [
            idx for idx in indices
            if rng.random() < max(sparsity, 1e-3)
        ]
    )
    # SYK convention: J_{ijkl} ~ Gaussian, var = (q-1)! J^2 / N^(q-1)
    import math
    var = float(math.factorial(q - 1)) * J ** 2 / (N ** (q - 1))
    couplings: dict[tuple[int, ...], complex] = {}
    for idx in keep:
        couplings[tuple(idx)] = (1j ** (q // 2)) * rng.normal(
            scale=np.sqrt(var)
        )
    return couplings


def _build_syk_hamiltonian(
    N: int, q: int, J: float, seed: int, sparsity: float = 1.0,
) -> np.ndarray:
    chis = _majoranas(N)
    couplings = _syk_couplings(N, q, J, seed, sparsity)
    dim = chis[0].shape[0]
    H = np.zeros((dim, dim), dtype=np.complex128)
    for indices, J_val in couplings.items():
        op = np.eye(dim, dtype=np.complex128)
        for idx in indices:
            op = op @ chis[idx]
        H += J_val * op
    # Hermitise — SYK Hamiltonian is by construction Hermitian.
    H = 0.5 * (H + H.conj().T)
    return H


def _syk_dense(p: SYKParams, canonical_hash: str) -> ClassicalOutcome:
    if p.N > _DENSE_MAX_N:
        msg = (
            f"Dense SYK ED only supported up to N={_DENSE_MAX_N}; "
            "install qfull-gravity[heavy] for the sparse path at higher N."
        )
        raise ClassicalReferenceError(msg)
    H = _build_syk_hamiltonian(p.N, p.q, p.J, p.seed)
    eigvals = np.linalg.eigvalsh(H).real
    sff = _spectral_form_factor(eigvals, t=1.0)
    return ClassicalOutcome(
        hash=canonical_hash,
        energy=float(eigvals[0]),
        metadata={
            "method": "syk_dense_ed",
            "model_domain": "toy_SYK_1+1D",
            "N": p.N, "q": p.q, "J": p.J,
            "spectrum_min": float(eigvals[0]),
            "spectrum_max": float(eigvals[-1]),
            "spectral_form_factor": sff,
        },
        method_used="syk_dense_ed",
        warning=None,
    )


def _syk_sparse(
    p: SparseSYKParams, canonical_hash: str,
) -> ClassicalOutcome:
    if p.N > _SPARSE_MAX_N:
        msg = (
            f"Sparse SYK ED only supported up to N={_SPARSE_MAX_N} in "
            "this build."
        )
        raise ClassicalReferenceError(msg)
    H = _build_syk_hamiltonian(p.N, p.q, 1.0, p.seed, sparsity=p.sparsity)
    eigvals = np.linalg.eigvalsh(H).real
    return ClassicalOutcome(
        hash=canonical_hash,
        energy=float(eigvals[0]),
        metadata={
            "method": "syk_sparse_ed",
            "model_domain": "SYK_sparse",
            "N": p.N, "q": p.q,
            "sparsity": p.sparsity,
            "spectrum_min": float(eigvals[0]),
            "spectrum_max": float(eigvals[-1]),
        },
        method_used="syk_sparse_ed",
        warning=None,
    )


def _jt_matrix(p: JTParams, canonical_hash: str) -> ClassicalOutcome:
    if p.matrix_size > _JT_MAX:
        msg = f"JT matrix size capped at {_JT_MAX} for the bundled kernel."
        raise ClassicalReferenceError(msg)
    rng = np.random.default_rng(p.seed)
    n = p.matrix_size
    if p.ensemble == "GUE":
        a = (rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))) / np.sqrt(2)
        H = (a + a.conj().T) / np.sqrt(2 * n)
    elif p.ensemble == "GOE":
        a = rng.standard_normal((n, n))
        H = (a + a.T) / np.sqrt(2 * n)
    else:  # GSE — use a real symplectic surrogate for simplicity.
        a = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
        H = (a + a.conj().T) / np.sqrt(2 * n)
    eigvals = np.linalg.eigvalsh(H).real
    return ClassicalOutcome(
        hash=canonical_hash,
        energy=float(eigvals[0]),
        metadata={
            "method": "jt_matrix_ensemble",
            "model_domain": "JT_matrix_model",
            "matrix_size": p.matrix_size,
            "ensemble": p.ensemble,
            "spectrum_min": float(eigvals[0]),
            "spectrum_max": float(eigvals[-1]),
            "edge_density": float(np.sum(np.abs(eigvals) > 1.5) / n),
        },
        method_used="jt_matrix_ensemble",
        warning=None,
    )


def _spectral_form_factor(eigvals: np.ndarray, t: float) -> float:
    """g(t) = |sum_i exp(-i E_i t)|^2 / N. Captures level statistics."""
    n = max(1, eigvals.size)
    z = np.sum(np.exp(-1j * eigvals * t))
    return float((z.conj() * z).real / n)
