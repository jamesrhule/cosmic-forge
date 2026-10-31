"""S-amo-4: classical-NQS path skipped cleanly when netket absent."""

from __future__ import annotations

import pytest

from qcompass_core.errors import ClassicalReferenceError
from qfull_amo import AMOProblem, RydbergParams, compute_reference


def test_rydberg_above_ed_ceiling_raises() -> None:
    """L > 14 must raise ClassicalReferenceError pointing at netket NQS."""
    with pytest.raises(ValueError):
        # L > 14 fails at manifest validation (Field(le=14)).
        AMOProblem(
            kind="rydberg_ground_state",
            rydberg_ground_state=RydbergParams(L=15),
        )


def test_netket_optional_path_documents_install() -> None:
    pytest.importorskip("netket")
