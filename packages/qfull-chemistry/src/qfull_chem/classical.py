"""Classical reference dispatcher.

Returns a :class:`ClassicalReferenceResult` for a
:class:`ChemistryProblem` by routing through:

- ``FCI``  → :class:`qcompass_core.PySCFAdapter` (live).
- ``CCSD(T)`` → ``pyscf.cc`` directly (light wrapper here; not
  promoted into qcompass-core because CCSD(T) is chemistry-specific).
- ``DMRG`` → ``pyblock2.driver.core.DMRGDriver`` if installed;
  otherwise raises :class:`ClassicalReferenceError`.

FeMoco-toy is the documented exception: the function returns a
sentinel ``hash="unavailable"`` and ``energy=float("nan")`` so the
M13 protocol stays type-stable.
"""

from __future__ import annotations

from typing import Any, TypedDict

from qcompass_core import PySCFAdapter, hash_payload
from qcompass_core.errors import ClassicalReferenceError

from .manifest import ChemistryProblem


class ClassicalOutcome(TypedDict):
    """Local extension of qcompass_core.ClassicalReferenceResult.

    ``method_used`` records which path actually produced the answer
    (FCI / CCSD / CCSD(T) / DMRG / unavailable) so the orchestrator
    can include it verbatim in the audit envelope.
    """

    hash: str
    energy: float
    metadata: dict[str, Any]
    method_used: str
    warning: str | None


_UNAVAILABLE = "unavailable"


def compute_reference(problem: ChemistryProblem) -> ClassicalOutcome:
    """Dispatch on ``problem.reference`` and return a unified outcome."""
    payload = problem.canonical_problem_payload()
    canonical_hash = hash_payload(payload)

    if problem.molecule == "FeMoco_toy":
        return ClassicalOutcome(
            hash=_UNAVAILABLE,
            energy=float("nan"),
            metadata={
                "method": "unavailable",
                "reason": (
                    "FeMoco-toy active space is beyond accessible classical "
                    "FCI/DMRG today; no reference recorded."
                ),
            },
            method_used="unavailable",
            warning="no_classical_reference",
        )

    if problem.reference == "FCI":
        return _fci(problem, canonical_hash)
    if problem.reference == "CCSD(T)":
        return _ccsd_t(problem, canonical_hash)
    if problem.reference == "DMRG":
        return _dmrg(problem, canonical_hash)

    msg = f"Unsupported classical reference: {problem.reference!r}"
    raise ClassicalReferenceError(msg)


# ── Path implementations ──────────────────────────────────────────────


def _fci(problem: ChemistryProblem, canonical_hash: str) -> ClassicalOutcome:
    """PySCF FCI through the M13 adapter."""
    if problem.geometry is None:
        msg = "FCI path requires problem.geometry"
        raise ClassicalReferenceError(msg)
    adapter = PySCFAdapter()
    res = adapter.compute({
        "atom": problem.geometry,
        "basis": problem.basis,
        "method": "fci",
        "charge": problem.charge,
        "spin": problem.spin,
    })
    return ClassicalOutcome(
        hash=canonical_hash,  # stable across machines
        energy=float(res["energy"]),
        metadata={**res["metadata"], "adapter_hash": res["hash"]},
        method_used="FCI",
        warning=None,
    )


def _ccsd_t(problem: ChemistryProblem, canonical_hash: str) -> ClassicalOutcome:
    """CCSD(T) via pyscf.cc.

    The qcompass-core M13 PySCFAdapter currently exposes only HF and
    FCI methods. CCSD(T) is chemistry-specific; we keep the wrapper
    here rather than enriching the core protocol.
    """
    try:
        from pyscf import cc, gto, scf
    except ImportError as exc:  # pragma: no cover - optional path
        msg = "pyscf is required for CCSD(T); install backend[chem]"
        raise ClassicalReferenceError(msg) from exc

    if problem.geometry is None:
        msg = "CCSD(T) path requires problem.geometry"
        raise ClassicalReferenceError(msg)

    mol = gto.Mole()
    mol.atom = problem.geometry
    mol.basis = problem.basis
    mol.charge = problem.charge
    mol.spin = problem.spin
    mol.verbose = 0
    mol.build()

    mf = scf.RHF(mol)
    mf.verbose = 0
    e_hf = float(mf.kernel())
    cc_solver = cc.CCSD(mf)
    cc_solver.verbose = 0
    e_corr_ccsd, _, _ = cc_solver.kernel()
    e_t = float(cc_solver.ccsd_t())
    energy = e_hf + float(e_corr_ccsd) + e_t

    return ClassicalOutcome(
        hash=canonical_hash,
        energy=energy,
        metadata={
            "method": "CCSD(T)",
            "basis": problem.basis,
            "n_electron": int(mol.nelectron),
            "n_orbital": int(mol.nao),
            "e_hf": e_hf,
            "e_ccsd_corr": float(e_corr_ccsd),
            "e_t_correction": e_t,
        },
        method_used="CCSD(T)",
        warning=None,
    )


def _dmrg(problem: ChemistryProblem, canonical_hash: str) -> ClassicalOutcome:
    """DMRG via pyblock2.driver if available.

    pyblock2's DMRGDriver expects integrals; we build them from PySCF
    so the manifest stays uniform with the FCI / CCSD(T) paths.
    """
    try:
        from pyblock2.driver.core import DMRGDriver, SymmetryTypes
    except ImportError as exc:  # pragma: no cover - optional path
        msg = (
            "pyblock2 is required for DMRG; install backend[chem] and "
            "ensure block2 is built."
        )
        raise ClassicalReferenceError(msg) from exc
    try:
        from pyscf import gto, scf
    except ImportError as exc:  # pragma: no cover - optional path
        msg = "pyscf is required for the DMRG integral build."
        raise ClassicalReferenceError(msg) from exc

    if problem.geometry is None:
        msg = "DMRG path requires problem.geometry"
        raise ClassicalReferenceError(msg)

    mol = gto.Mole()
    mol.atom = problem.geometry
    mol.basis = problem.basis
    mol.charge = problem.charge
    mol.spin = problem.spin
    mol.verbose = 0
    mol.build()

    mf = scf.RHF(mol)
    mf.verbose = 0
    mf.kernel()

    n_orb = int(mol.nao)
    n_elec = int(mol.nelectron)
    if problem.active_space is not None:
        n_elec, n_orb = problem.active_space

    driver = DMRGDriver(scratch="/tmp/qfull_chem_dmrg", symm_type=SymmetryTypes.SU2)
    driver.initialize_system(n_sites=n_orb, n_elec=n_elec, spin=problem.spin)

    # Lightweight DMRG: the absolute number isn't the point of S-chem-2;
    # what matters is that we round-trip the protocol and the energy
    # is finite.
    try:
        h1e = mf.get_hcore()
        eri = mol.intor("int2e")
        ecore = float(mol.energy_nuc())
        mpo = driver.get_qc_mpo(h1e=h1e, g2e=eri, ecore=ecore, iprint=0)
        ket = driver.get_random_mps(tag="GS", bond_dim=200)
        energy = float(driver.dmrg(mpo, ket, n_sweeps=8, bond_dims=[100, 200, 400]))
    except Exception as exc:
        msg = f"pyblock2 DMRG failed: {exc}"
        raise ClassicalReferenceError(msg) from exc

    return ClassicalOutcome(
        hash=canonical_hash,
        energy=energy,
        metadata={
            "method": "DMRG",
            "basis": problem.basis,
            "n_electron": n_elec,
            "n_orbital": n_orb,
        },
        method_used="DMRG",
        warning=None,
    )
