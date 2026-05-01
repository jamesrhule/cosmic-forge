"""S-bench-2: every successful run records a non-empty provenance hash."""

from __future__ import annotations

from pathlib import Path

import pytest

from qcompass_bench import LeaderboardStore, run_bench


@pytest.fixture
def isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LeaderboardStore:
    """Per-test SQLite store under tmp_path."""
    db_path = tmp_path / "leaderboard.sqlite"
    monkeypatch.setenv("QCOMPASS_BENCH_DB", str(db_path))
    monkeypatch.setenv("QCOMPASS_ARTIFACTS", str(tmp_path / "artifacts"))
    return LeaderboardStore(db_path=db_path)


def test_h2_chemistry_run_records_hash(
    isolated_store: LeaderboardStore, tmp_path: Path,
) -> None:
    pytest.importorskip("pyscf")
    rows = run_bench(
        domains=["chemistry"],
        instance="h2",
        store=isolated_store,
        artifacts_root=tmp_path / "artifacts",
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.ok is True
    assert row.provenance_hash != ""
    assert row.provenance_hash != "unavailable"
    assert row.classical_energy is not None


def test_femoco_run_records_unavailable_sentinel(
    isolated_store: LeaderboardStore, tmp_path: Path,
) -> None:
    rows = run_bench(
        domains=["chemistry"],
        instance="femoco_toy",
        store=isolated_store,
        artifacts_root=tmp_path / "artifacts",
    )
    assert len(rows) == 1
    row = rows[0]
    # FeMoco_toy.backend_preference defaults to "dice"; on non-Linux
    # without qiskit-addon-dice-solver this raises and the row is
    # marked ok=False. Either way, the provenance hash slot is
    # populated (with the documented "unavailable" sentinel when the
    # classical reference is absent).
    assert row.provenance_hash
    if row.ok:
        assert row.provenance_hash == "unavailable"
