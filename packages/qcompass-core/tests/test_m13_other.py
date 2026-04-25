"""Soft-import M13 adapters: contract is fixed, drivers land later."""

from __future__ import annotations

import pytest

from qcompass_core import (
    Block2Adapter,
    ClassicalReferenceError,
    IpieAdapter,
    QuimbAdapter,
    hash_payload,
)


def test_block2_hash_only_matches_canonical() -> None:
    h = Block2Adapter().hash_only({"x": 1, "y": [1, 2]})
    assert h == hash_payload({"y": [1, 2], "x": 1})


def test_quimb_hash_only_matches_canonical() -> None:
    h = QuimbAdapter().hash_only({"a": 1})
    assert h == hash_payload({"a": 1})


@pytest.mark.parametrize("adapter_cls", [Block2Adapter, QuimbAdapter, IpieAdapter])
def test_unwired_adapters_raise(adapter_cls: type) -> None:
    adapter = adapter_cls()
    with pytest.raises(ClassicalReferenceError):
        adapter.compute({"x": 1})
