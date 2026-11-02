"""TFermion adapter (research code, optional vendoring)."""

from __future__ import annotations

from typing import Any

from ..errors import ResourceEstimationError
from ..manifest import Manifest, ResourceEstimate


class TFermionAdapter:
    """TFermion wrapper.

    TFermion has no stable PyPI release; pin a research SHA via the
    [research] extra and vendor the wheel locally.
    """

    name: str = "tfermion"

    def estimate(self, manifest: Manifest, payload: Any) -> ResourceEstimate:
        try:
            import tfermion  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional
            msg = (
                "tfermion is not installed. Vendor a known SHA into the "
                "qcompass-core[research] extra to use this adapter."
            )
            raise ResourceEstimationError(msg) from exc

        _ = tfermion, manifest, payload  # type: ignore[unused-ignore]
        msg = "TFermionAdapter.estimate is not yet wired."
        raise ResourceEstimationError(msg)
