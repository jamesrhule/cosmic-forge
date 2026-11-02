from __future__ import annotations

from pathlib import Path

import pytest

from qfull_hep import HEPProblem, load_instance


@pytest.fixture(scope="session")
def schwinger_l4() -> HEPProblem:
    return load_instance("schwinger_l4")


@pytest.fixture(scope="session")
def schwinger_l6() -> HEPProblem:
    return load_instance("schwinger_l6")


@pytest.fixture(scope="session")
def schwinger_l10() -> HEPProblem:
    return load_instance("schwinger_l10")


@pytest.fixture
def artifacts_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"
