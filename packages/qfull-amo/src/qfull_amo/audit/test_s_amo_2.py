"""S-amo-2: MIS toy returns the optimal independent set."""

from __future__ import annotations

from qfull_amo import AMOProblem, compute_reference


def test_mis_path_5_returns_optimal(mis_path_5: AMOProblem) -> None:
    outcome = compute_reference(mis_path_5)
    meta = outcome["metadata"]
    # 5-node path graph: max independent set has size 3 ({0, 2, 4}).
    assert meta["mis_size"] == 3
    chosen = set(meta["mis_set"])
    edges = {(0, 1), (1, 2), (2, 3), (3, 4)}
    assert all((a in chosen) != (b in chosen) or not ((a in chosen) and (b in chosen)) for a, b in edges)
    assert outcome["energy"] == -3.0
