from __future__ import annotations

from pathlib import Path

import pytest

from qfull_cm import CondMatProblem, load_instance


@pytest.fixture(scope="session")
def heisenberg_problem() -> CondMatProblem:
    return load_instance("heisenberg_chain_10")


@pytest.fixture(scope="session")
def hubbard_problem() -> CondMatProblem:
    return load_instance("hubbard_4x4")


@pytest.fixture(scope="session")
def otoc_problem() -> CondMatProblem:
    return load_instance("otoc_chain_8")


@pytest.fixture
def artifacts_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"
