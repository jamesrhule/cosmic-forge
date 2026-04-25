"""Always-available stub estimator.

Returns a deterministic placeholder :class:`ResourceEstimate` so the
pipeline can be exercised end-to-end without any external SDK.
"""

from __future__ import annotations

from typing import Any

from ..manifest import Manifest, ResourceEstimate


class StubEstimator:
    """In-process stub used by tests and CI."""

    name: str = "stub"

    def estimate(self, manifest: Manifest, payload: Any) -> ResourceEstimate:
        # The stub scales loosely with the manifest's payload size so
        # tests can assert that bigger problems get bigger estimates.
        size = max(1, len(str(manifest.problem)) // 32)
        return ResourceEstimate(
            physical_qubits=64 * size,
            logical_qubits=4 * size,
            t_count=512 * size,
            rotation_count=128 * size,
            depth=256 * size,
            runtime_seconds=1.0 * size,
            estimator="stub",
            notes="StubEstimator: placeholder. Install [azure] for real numbers.",
        )
