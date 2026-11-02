"""LQCD-HDF5 stub tests (PROMPT 0 v2)."""

from __future__ import annotations

from pathlib import Path

import h5py
import pytest

from qcompass_core import HamiltonianFormatError, LQCDHDF5Schema, read_lqcd_hdf5


def test_read_lqcd_hdf5_round_trips(tmp_path: Path) -> None:
    """Stub reader populates the schema from root-group attrs + keys."""
    p = tmp_path / "lqcd.h5"
    with h5py.File(str(p), "w") as f:
        f.attrs["lattice_shape"] = [16, 8, 8, 8]
        f.attrs["gauge_group"] = "SU(3)"
        f.attrs["quark_action"] = "Wilson"
        f.attrs["n_flavors"] = 2
        # A few placeholder operator datasets at the root.
        f.create_dataset("Q1", data=[1.0])
        f.create_dataset("Q2", data=[2.0])

    schema = read_lqcd_hdf5(p)
    assert isinstance(schema, LQCDHDF5Schema)
    assert schema.lattice_shape == (16, 8, 8, 8)
    assert schema.gauge_group == "SU(3)"
    assert schema.quark_action == "Wilson"
    assert schema.n_flavors == 2
    assert set(schema.operator_keys) == {"Q1", "Q2"}


def test_missing_file_raises() -> None:
    with pytest.raises(HamiltonianFormatError, match="not found"):
        read_lqcd_hdf5(Path("/this/path/does/not/exist.h5"))


def test_bad_lattice_shape_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.h5"
    with h5py.File(str(p), "w") as f:
        f.attrs["lattice_shape"] = [16, 8]  # only 2 dims
    with pytest.raises(HamiltonianFormatError, match="4-tuple"):
        read_lqcd_hdf5(p)
