from __future__ import annotations

from pathlib import Path

import pytest

from qfull_amo import AMOProblem, load_instance


@pytest.fixture(scope="session")
def rydberg_chain_8() -> AMOProblem:
    return load_instance("rydberg_chain_8")


@pytest.fixture(scope="session")
def rydberg_ring_6() -> AMOProblem:
    return load_instance("rydberg_ring_6")


@pytest.fixture(scope="session")
def mis_path_5() -> AMOProblem:
    return load_instance("mis_path_5")


@pytest.fixture
def artifacts_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"
