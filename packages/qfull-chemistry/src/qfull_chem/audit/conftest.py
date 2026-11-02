"""Shared fixtures for the qfull-chemistry per-domain audit suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from qfull_chem import ChemistryProblem, load_instance


@pytest.fixture(scope="session")
def h2_problem() -> ChemistryProblem:
    return load_instance("h2")


@pytest.fixture(scope="session")
def lih_problem() -> ChemistryProblem:
    return load_instance("lih")


@pytest.fixture(scope="session")
def n2_problem() -> ChemistryProblem:
    return load_instance("n2")


@pytest.fixture(scope="session")
def femoco_problem() -> ChemistryProblem:
    return load_instance("femoco_toy")


@pytest.fixture
def artifacts_dir(tmp_path: Path) -> Path:
    """Per-test sandbox for provenance sidecars."""
    return tmp_path / "artifacts"
