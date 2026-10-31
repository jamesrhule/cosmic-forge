"""Azure Quantum Resource Estimator adapter.

Imports :mod:`azure.quantum` lazily; if the package is missing the
adapter still loads but :meth:`estimate` raises
:class:`ResourceEstimationError` with a clear hint about
``pip install qcompass-core[azure]``.
"""

from __future__ import annotations

from typing import Any

from ..errors import ResourceEstimationError
from ..manifest import Manifest, ResourceEstimate


class AzureMicrosoftEstimatorAdapter:
    """Wraps Microsoft's QRE behind the QCompass :class:`QEstimator` shape."""

    name: str = "microsoft"

    def __init__(self, *, workspace: object | None = None) -> None:
        # `workspace` is optional so the adapter can be constructed in
        # tests without an Azure account; estimate() will fail loudly
        # if the workspace is needed but absent.
        self._workspace = workspace

    def estimate(self, manifest: Manifest, payload: Any) -> ResourceEstimate:
        try:
            from azure.quantum import Workspace  # type: ignore[import-not-found]
            from azure.quantum.target.microsoft import (  # type: ignore[import-not-found]
                MicrosoftEstimator,
            )
        except ImportError as exc:  # pragma: no cover - optional path
            msg = (
                "azure-quantum is not installed. Install with "
                "`pip install qcompass-core[azure]`."
            )
            raise ResourceEstimationError(msg) from exc

        if self._workspace is None:
            msg = "AzureMicrosoftEstimatorAdapter requires a workspace handle."
            raise ResourceEstimationError(msg)

        # Wire the call so type-checkers see the API surface; the
        # actual submission/polling logic is a Phase-2 deliverable.
        _ = Workspace, MicrosoftEstimator  # noqa: F841 — see comment above
        msg = (
            "AzureMicrosoftEstimatorAdapter.estimate is wired but not yet "
            "live; submit your manifest via the Azure portal or wait for "
            "Phase-2 of qcompass-core."
        )
        raise ResourceEstimationError(msg)
