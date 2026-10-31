"""Classical reference for the AMO domain.

- Rydberg-blockade ground state via dense ED on a 2^L spin chain
  (each atom maps to a |g⟩ / |r⟩ qubit). Blockade is enforced as
  an energy penalty on adjacent excited pairs.
- MIS toy: brute-force enumerate the bit strings on the graph and
  pick the maximum independent set. ``energy = -|MIS|`` so the
  global minimum encodes the optimum.

netket NQS is the planned backend for L > 14; lazy-imported.
"""

from __future__ import annotations

from itertools import product
from typing import Any, TypedDict

import numpy as np

from qcompass_core import hash_payload
from qcompass_core.errors import ClassicalReferenceError

from .manifest import AMOProblem, MISParams, RydbergParams


class ClassicalOutcome(TypedDict):
    hash: str
    energy: float
    metadata: dict[str, Any]
    method_used: str
    warning: str | None


_ED_MAX_L = 14


def compute_reference(problem: AMOProblem) -> ClassicalOutcome:
    h = hash_payload(problem.canonical_payload())
    if problem.kind == "rydberg_ground_state":
        assert problem.rydberg_ground_state is not None
        return _rydberg(problem.rydberg_ground_state, h)
    if problem.kind == "mis_toy":
        assert problem.mis_toy is not None
        return _mis(problem.mis_toy, h)
    msg = f"Unsupported AMO kind: {problem.kind!r}"
    raise ClassicalReferenceError(msg)


def _rydberg(p: RydbergParams, canonical_hash: str) -> ClassicalOutcome:
    if p.L > _ED_MAX_L:
        msg = (
            f"Rydberg ED only supported up to L={_ED_MAX_L}; "
            "netket NQS is the planned backend."
        )
        raise ClassicalReferenceError(msg)
    H = _rydberg_hamiltonian(p)
    eigvals = np.linalg.eigvalsh(H)
    e0 = float(eigvals[0])
    return ClassicalOutcome(
        hash=canonical_hash,
        energy=e0,
        metadata={
            "method": "rydberg_ed",
            "L": p.L,
            "blockade_radius": p.blockade_radius,
            "detuning": p.detuning,
            "rabi": p.rabi,
            "geometry": p.geometry,
            "energy_per_atom": e0 / p.L,
        },
        method_used="rydberg_ed",
        warning=None,
    )


def _rydberg_hamiltonian(p: RydbergParams) -> np.ndarray:
    """H = -(Ω/2) Σ σ^x_i + Σ Δ n_i + V Σ n_i n_{i+1}.

    Where n_i = (1 - σ^z_i)/2 (Rydberg occupation), V is a large
    blockade penalty derived from blockade_radius.
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

    # Drive: -(Ω/2) σ^x_i.
    for i in range(L):
        ops: list[np.ndarray] = [iden] * L
        ops[i] = sx
        H += -0.5 * p.rabi * kron_chain(ops)

    # Detuning: -Δ n_i = -Δ (1 - σ^z_i)/2 → -Δ/2 * I + Δ/2 σ^z_i.
    for i in range(L):
        ops_id: list[np.ndarray] = [iden] * L
        ops_z: list[np.ndarray] = [iden] * L
        ops_z[i] = sz
        H += -0.5 * p.detuning * kron_chain(ops_id)
        H += +0.5 * p.detuning * kron_chain(ops_z)

    # Blockade penalty on nearest-neighbour double excitations.
    V = 50.0 / max(p.blockade_radius**6, 1e-9)  # van-der-Waals scaling
    pairs = [(i, i + 1) for i in range(L - 1)]
    if p.geometry == "ring":
        pairs.append((L - 1, 0))
    for i, j in pairs:
        ops_id_a: list[np.ndarray] = [iden] * L
        ops_z_a: list[np.ndarray] = [iden] * L
        ops_z_a[i] = sz
        ops_id_b: list[np.ndarray] = [iden] * L
        ops_z_b: list[np.ndarray] = [iden] * L
        ops_z_b[j] = sz
        ops_z_ab: list[np.ndarray] = [iden] * L
        ops_z_ab[i] = sz
        ops_z_ab[j] = sz
        # n_i n_j = (1 - σ^z_i)(1 - σ^z_j)/4 = 1/4 [1 - z_i - z_j + z_i z_j]
        H += V * 0.25 * kron_chain(ops_id_a)
        H -= V * 0.25 * kron_chain(ops_z_a)
        H -= V * 0.25 * kron_chain(ops_z_b)
        H += V * 0.25 * kron_chain(ops_z_ab)
    return H


def _mis(p: MISParams, canonical_hash: str) -> ClassicalOutcome:
    """Brute-force MIS — fine for n_nodes ≤ 12."""
    n = p.n_nodes
    if n > 12:
        msg = (
            f"MIS brute-force ceiling is 12 nodes; got {n}. "
            "Use the classical NQS / quantum schedule for larger graphs."
        )
        raise ClassicalReferenceError(msg)
    edges = {(min(a, b), max(a, b)) for a, b in p.edges}
    best_size = 0
    best_set: tuple[int, ...] = ()
    for bits in product([0, 1], repeat=n):
        chosen = tuple(i for i, b in enumerate(bits) if b)
        if any((a in chosen) and (b in chosen) for a, b in edges):
            continue
        if len(chosen) > best_size:
            best_size = len(chosen)
            best_set = chosen
    return ClassicalOutcome(
        hash=canonical_hash,
        energy=float(-best_size),
        metadata={
            "method": "mis_brute_force",
            "n_nodes": n,
            "n_edges": len(edges),
            "mis_size": best_size,
            "mis_set": list(best_set),
        },
        method_used="mis_brute_force",
        warning=None,
    )
