# `qfull-condmat`

Condensed-matter domain plugin for QCompass. Module: `qfull_cm`.

## Domains

- Hubbard model (1D / 2D, exact diag for small systems; DMRG via
  tenpy for chains; quimb for tensor-network ansatz).
- Heisenberg model (XXZ, frustrated; tenpy / netket).
- Out-of-time-order correlator (OTOC) — **Quantum-Echoes / Willow
  pattern** (Loschmidt-echo OTOC on 65-qubit IBM Heron, Mi et al.
  *Nature* 2024 / Andersen et al. arXiv:2310.06813). Classical
  reference: scipy time-evolution for short chains; netket NQS
  for >20 sites.

## Backends

| Path | Backend | Module | Extra |
|---|---|---|---|
| Classical | quimb / tenpy / netket / scipy | `classical.py` | `[classical]` |
| Digital QPU | IBM Heron via qiskit-ibm-runtime | `quantum_ibm.py` | `[ibm]` |
| Analog QPU | QuEra Aquila via bloqade-analog | `quantum_analog.py` | `[analog]` |

## Boundary

This package MUST NOT import from `ucgle_f1` or any other `qfull_*`
sibling. CI enforces with both a grep guard and
`tests/test_boundary.py`.

## Audit

| Check | Description |
|---|---|
| S-cm-1 | Hubbard 4×4 (U=4) DMRG ground-state energy within 1 mHa of exact diag |
| S-cm-2 | Heisenberg chain L=10 ED ground state matches the canonical −0.4438... per site |
| S-cm-3 | OTOC fidelity vs classical reference within 5% on the L=8 short-chain reference |
| S-cm-4 | OTOC chain-length feasibility flag set when L > 24 (memory bound) |
| S-cm-5 | ProvenanceRecord present + classical_reference_hash recorded |

## Tests

```bash
uv run --package qfull-condmat pytest -q
mypy --strict src/qfull_cm
```
