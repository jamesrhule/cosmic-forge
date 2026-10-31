"""PySCF adapter (HF + FCI for small systems)."""

from __future__ import annotations

from typing import Any

from ..errors import ClassicalReferenceError
from .base import ClassicalReferenceResult, hash_payload


class PySCFAdapter:
    """Wraps PySCF's RHF + FCI for small reference computations.

    The adapter is intentionally minimal: callers pass an atom string
    (PySCF format), basis name, and optional ``method`` ('hf' or
    'fci'). Larger workflows should go through qfull-chemistry, which
    layers in active-space selection, density fitting, etc.
    """

    name: str = "pyscf"

    def compute(self, problem: dict[str, Any]) -> ClassicalReferenceResult:
        try:
            from pyscf import fci, gto, scf  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional
            msg = (
                "PySCF is not installed. Run `pip install qcompass-core[chem]` "
                "to enable PySCFAdapter."
            )
            raise ClassicalReferenceError(msg) from exc

        atom = problem.get("atom")
        basis = problem.get("basis", "sto-3g")
        method = problem.get("method", "hf").lower()
        if not atom:
            msg = "PySCFAdapter requires problem['atom']."
            raise ClassicalReferenceError(msg)

        mol = gto.Mole()
        mol.atom = atom
        mol.basis = basis
        mol.charge = int(problem.get("charge", 0))
        mol.spin = int(problem.get("spin", 0))
        mol.verbose = 0
        mol.build()

        mf = scf.RHF(mol)
        mf.verbose = 0
        e_hf = float(mf.kernel())

        if method == "hf":
            energy = e_hf
            metadata: dict[str, Any] = {
                "method": "RHF",
                "basis": basis,
                "n_electron": int(mol.nelectron),
                "n_orbital": int(mol.nao),
            }
        elif method == "fci":
            cisolver = fci.FCI(mol, mf.mo_coeff)
            e_fci, _ = cisolver.kernel()
            energy = float(e_fci)
            metadata = {
                "method": "FCI",
                "basis": basis,
                "n_electron": int(mol.nelectron),
                "n_orbital": int(mol.nao),
                "e_hf": e_hf,
            }
        else:
            msg = f"Unsupported PySCF method '{method}'."
            raise ClassicalReferenceError(msg)

        return {
            "hash": hash_payload({"atom": atom, "basis": basis,
                                  "method": method,
                                  "charge": mol.charge, "spin": mol.spin}),
            "energy": energy,
            "metadata": metadata,
        }
