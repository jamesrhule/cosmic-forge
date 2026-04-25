"""M11 — FCIDUMP reader + spin-Hamiltonian validator tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from qcompass_core import (
    HamiltonianFormatError,
    SpinHamiltonian,
    read_fcidump,
    validate_spin_hamiltonian,
)


_SAMPLE = """\
&FCI NORB=2,NELEC=2,MS2=0,
ORBSYM=1,1,
ISYM=1
&END
  1.0  1  1  1  1
  0.5  1  2  2  1
  0.0  0  0  0  0
"""


def test_fcidump_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "fcidump"
    p.write_text(_SAMPLE)
    h = read_fcidump(p)
    assert h.norb == 2
    assert h.nelec == 2
    assert h.ms2 == 0
    assert h.nuclear_repulsion == 0.0
    # Two non-zero integral lines + the (0,0,0,0) terminator.
    assert len(h.integrals) == 2


def test_fcidump_rejects_bad_header(tmp_path: Path) -> None:
    p = tmp_path / "bad"
    p.write_text("&FCI X=1, &END\n")
    with pytest.raises(HamiltonianFormatError):
        read_fcidump(p)


def test_spin_hamiltonian_basic() -> None:
    sh = validate_spin_hamiltonian({
        "n_sites": 4,
        "spin": 0.5,
        "site_terms": [
            {"site": 0, "op": "X", "coeff": 1.0},
            {"site": 3, "op": "Z", "coeff": 0.5},
        ],
        "pair_terms": [
            {"site_a": 0, "site_b": 1, "op_a": "Z", "op_b": "Z", "coeff": -1.0},
        ],
        "boundary": "periodic",
    })
    assert isinstance(sh, SpinHamiltonian)
    assert sh.boundary == "periodic"


def test_spin_hamiltonian_rejects_out_of_range_site() -> None:
    with pytest.raises(HamiltonianFormatError):
        validate_spin_hamiltonian({
            "n_sites": 2,
            "site_terms": [{"site": 5, "op": "X", "coeff": 1.0}],
            "pair_terms": [],
        })
