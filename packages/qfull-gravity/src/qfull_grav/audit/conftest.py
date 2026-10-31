from __future__ import annotations

from pathlib import Path

import pytest

from qfull_grav import GravityProblem, load_instance


@pytest.fixture(scope="session")
def syk_n8() -> GravityProblem:
    return load_instance("syk_n8")


@pytest.fixture(scope="session")
def syk_sparse_n12() -> GravityProblem:
    return load_instance("syk_sparse_n12")


@pytest.fixture(scope="session")
def jt_n16() -> GravityProblem:
    return load_instance("jt_n16")


@pytest.fixture(scope="session")
def syk_learned_n8() -> GravityProblem:
    return load_instance("syk_learned_n8")


@pytest.fixture
def artifacts_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"
