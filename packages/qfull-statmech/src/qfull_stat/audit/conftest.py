from __future__ import annotations

from pathlib import Path

import pytest

from qfull_stat import StatmechProblem, load_instance


@pytest.fixture(scope="session")
def qae_bell() -> StatmechProblem:
    return load_instance("qae_bell")


@pytest.fixture(scope="session")
def metropolis_l6() -> StatmechProblem:
    return load_instance("metropolis_ising_l6")


@pytest.fixture(scope="session")
def tfd_l4() -> StatmechProblem:
    return load_instance("tfd_l4")


@pytest.fixture
def artifacts_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"
