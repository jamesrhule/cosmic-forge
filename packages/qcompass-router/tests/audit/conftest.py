"""Audit-suite fixtures.

Each test gets an isolated SQLite calibration cache and pricing cache
under `tmp_path` so the audit suite never reads or writes
~/.cache/qcompass/.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qcompass_router.calibration import CalibrationCache
from qcompass_router.pricing import FreeTierLedger, PricingEngine


@pytest.fixture
def calibration_cache(tmp_path: Path) -> CalibrationCache:
    return CalibrationCache(db_path=tmp_path / "cal.sqlite")


@pytest.fixture
def pricing_cache_dir(tmp_path: Path) -> Path:
    p = tmp_path / "pricing-cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture
def pricing_engine(pricing_cache_dir: Path) -> PricingEngine:
    return PricingEngine(cache_dir=pricing_cache_dir)


@pytest.fixture
def fresh_ledger(pricing_engine: PricingEngine) -> FreeTierLedger:
    # Snapshot the seed-derived ledger so individual tests can mutate
    # without affecting other tests.
    snap = FreeTierLedger()
    for name, bucket in pricing_engine.ledger.buckets.items():
        snap.buckets[name] = type(bucket)(
            units=bucket.units,
            unit_kind=bucket.unit_kind,
            applicable_backends=bucket.applicable_backends,
        )
    return snap
