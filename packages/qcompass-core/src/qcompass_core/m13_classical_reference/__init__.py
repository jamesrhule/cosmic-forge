"""M13 — Classical reference adapters.

Soft-import wrappers around PySCF (HF / FCI), block2 (DMRG), quimb
(MPS / TN), and ipie (AFQMC). Each adapter exposes a single
:func:`compute` returning a uniform dict::

    {"hash": str, "energy": float, "metadata": dict[str, Any]}

so plugins can attach a classical reference to their
:class:`ProvenanceRecord` without coupling to the specific reference
backend.
"""

from __future__ import annotations

from .base import ClassicalReference, hash_payload
from .ipie_adapter import IpieAdapter
from .pyscf_adapter import PySCFAdapter
from .quimb_adapter import QuimbAdapter
from .block2_adapter import Block2Adapter

__all__ = [
    "Block2Adapter",
    "ClassicalReference",
    "IpieAdapter",
    "PySCFAdapter",
    "QuimbAdapter",
    "hash_payload",
]
