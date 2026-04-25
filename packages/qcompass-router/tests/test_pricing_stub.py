"""Stub pricing seed YAML loads and `estimate(...)` is deterministic."""

from __future__ import annotations

import math

import pytest

from qcompass_router import pricing_stub


def test_local_backends_cost_zero() -> None:
    assert pricing_stub.estimate("local_aer", "", 1024) == 0.0
    assert pricing_stub.estimate("local_lightning", "", 1024) == 0.0


def test_braket_pricing_uses_per_shot_and_per_task() -> None:
    cost = pricing_stub.estimate("braket", "ionq_aria", 100)
    # per_task_usd=0.30, per_shot_usd=0.03 → 0.30 + 100*0.03 = 3.30
    assert math.isclose(cost, 3.30, rel_tol=1e-9)


def test_quera_per_shot() -> None:
    cost = pricing_stub.estimate("quera", "aquila", 200)
    assert math.isclose(cost, 200 * 0.01, rel_tol=1e-9)


def test_unknown_pair_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        pricing_stub.estimate("does-not", "exist", 10)


def test_negative_shots_rejected() -> None:
    with pytest.raises(ValueError):
        pricing_stub.estimate("local_aer", "", -1)
