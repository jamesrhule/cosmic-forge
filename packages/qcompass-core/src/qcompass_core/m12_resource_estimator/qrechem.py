"""QREChem adapter (research code, optional vendoring).

Treated as optional: if the Python module is unavailable
:meth:`estimate` raises :class:`ResourceEstimationError` so callers
fall back to :class:`StubEstimator` or
:class:`AzureMicrosoftEstimatorAdapter`.
"""

from __future__ import annotations

from typing import Any

from ..errors import ResourceEstimationError
from ..manifest import Manifest, ResourceEstimate


class QREChemAdapter:
    """QREChem wrapper. Vendor or pin a research SHA via ``[research]``."""

    name: str = "qrechem"

    def estimate(self, manifest: Manifest, payload: Any) -> ResourceEstimate:
        try:
            import qrechem  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional
            msg = (
                "qrechem is not installed. Vendor or install via the "
                "[research] extra and pin the upstream SHA."
            )
            raise ResourceEstimationError(msg) from exc

        _ = qrechem, manifest, payload  # type: ignore[unused-ignore]
        msg = "QREChemAdapter.estimate is not yet wired."
        raise ResourceEstimationError(msg)
