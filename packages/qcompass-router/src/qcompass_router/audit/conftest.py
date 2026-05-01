"""Audit fixtures for the qcompass-router."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from qcompass_router import (
    BraketAdapter,
    CalibrationCache,
    CalibrationSnapshot,
    IBMAdapter,
    LocalAerAdapter,
    Router,
)


# Adapters that pretend their SDK is available so audit tests can
# exercise the real routing logic without installing 9 vendor SDKs.

class _Aer(LocalAerAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


class _IBM(IBMAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


class _Braket(BraketAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


@pytest.fixture
def stub_router() -> Router:
    """Router with the 3 most relevant adapters always available."""
    return Router(providers=[_Aer(), _IBM(), _Braket()])


@pytest.fixture
def calibration_cache(tmp_path: Path) -> CalibrationCache:
    """Per-test calibration cache that doesn't pollute ~/.cache."""
    return CalibrationCache(db_path=tmp_path / "calib.sqlite")


def seed_history(
    cache: CalibrationCache,
    *,
    provider: str,
    backend: str,
    days: int,
    base_two_q: float = 0.01,
    base_readout: float = 0.02,
    base_t1_t2: float = 100.0,
) -> None:
    """Seed ``days`` of stable history before today."""
    today = date.today()
    for d in range(1, days + 1):
        snap = CalibrationSnapshot(
            provider=provider,
            backend=backend,
            day=today - timedelta(days=d),
            two_qubit_error=base_two_q,
            readout_error=base_readout,
            t1_t2_us=base_t1_t2,
        )
        cache.record(snap)
