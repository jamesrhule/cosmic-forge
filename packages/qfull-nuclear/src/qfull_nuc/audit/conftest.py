from __future__ import annotations

from pathlib import Path

import pytest

from qfull_nuc import NuclearProblem, load_instance


@pytest.fixture(scope="session")
def zero_nu_bb_l4() -> NuclearProblem:
    return load_instance("zero_nu_bb_l4")


@pytest.fixture(scope="session")
def ncsm_2body() -> NuclearProblem:
    return load_instance("ncsm_2body")


@pytest.fixture(scope="session")
def heavy_neutrino_mixing() -> NuclearProblem:
    return load_instance("heavy_neutrino_mixing")


@pytest.fixture(scope="session")
def sterile_neutrino_osc() -> NuclearProblem:
    return load_instance("sterile_neutrino_osc")


@pytest.fixture
def artifacts_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"
