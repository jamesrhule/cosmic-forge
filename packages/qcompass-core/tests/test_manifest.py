"""Manifest envelope tests."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from qcompass_core import (
    BackendRequest,
    Manifest,
    ProvenanceRecord,
    ResourceEstimate,
    emit_provenance,
)


def _example_manifest() -> Manifest:
    return Manifest(
        domain="null",
        version="1.0.0",
        problem={"label": "demo", "size": 4},
        backend_request=BackendRequest(kind="classical", shots=128, seed=7),
    )


def test_manifest_round_trip_is_bit_identical() -> None:
    m = _example_manifest()
    blob = m.model_dump_json()
    parsed = json.loads(blob)
    again = Manifest.model_validate(parsed)
    assert again.model_dump() == m.model_dump()


def test_manifest_rejects_unknown_domain() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate({
            "domain": "warp",
            "version": "1.0",
            "problem": {"x": 1},
            "backend_request": {"kind": "classical"},
        })


def test_manifest_rejects_empty_problem() -> None:
    with pytest.raises(ValidationError):
        Manifest(
            domain="null",
            version="1.0",
            problem={},
            backend_request=BackendRequest(kind="classical"),
        )


def test_manifest_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate({
            "domain": "null",
            "version": "1.0",
            "problem": {"x": 1},
            "backend_request": {"kind": "classical"},
            "secret": "leaked",  # extra="forbid"
        })


def test_provenance_record_required_field() -> None:
    rec = ProvenanceRecord(classical_reference_hash="abc")
    assert rec.classical_reference_hash == "abc"
    assert rec.resource_estimate is None


def test_emit_provenance_helper() -> None:
    estimate = ResourceEstimate(
        physical_qubits=1, logical_qubits=1, t_count=0,
        rotation_count=0, depth=1, runtime_seconds=0.0,
        estimator="stub",
    )
    rec = emit_provenance("h", estimate=estimate, calibration_hash="cal")
    assert rec.resource_estimate == estimate
    assert rec.device_calibration_hash == "cal"
