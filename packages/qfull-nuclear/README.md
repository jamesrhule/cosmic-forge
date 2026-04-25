# `qfull-nuclear`

Ab-initio nuclear / 0νββ domain plugin for QCompass. Module:
`qfull_nuc`.

## Domains

- 1+1D 0νββ toy per Chernyshev et al. *Nature Communications* 2026
  (s41467-026-68536-8). Every quantum result is flagged
  `model_domain: 1+1D_toy` in `ProvenanceRecord.error_mitigation_config`.
- Few-body NCSM matrix elements (2-4 body for now).

## Backends

| Path | Backend | Module | Extra |
|---|---|---|---|
| Classical | block2 DMRG / numpy ED for ≤ 8 sites | `classical.py` | `[classical]` |
| Quantum (preferred) | IonQ Forte via amazon-braket-sdk | `quantum_ionq.py` | `[ionq]` |
| Quantum (fallback) | IBM Heron via qiskit-ibm-runtime | `quantum_ibm.py` | `[ibm]` |
| Shell model | pyNSMC / nushellx (vendored on demand) | placeholder | `[shellmodel]` |

## Boundary

Must NOT import from `ucgle_f1` or any other `qfull_*`. Enforced by
`tests/test_boundary.py` + the CI grep step.

## Audit (S-nuc-1..5)

| Check | Description |
|---|---|
| S-nuc-1 | 0νββ toy L=4: ground-state energy matches dense ED to 1e-10 |
| S-nuc-2 | Half-filled occupancy is consistent with the toy charge sector |
| S-nuc-3 | Two-body NCSM matrix element is finite and antisymmetric in (i, j) |
| S-nuc-4 | block2 DMRG path skipped cleanly when pyblock2 absent |
| S-nuc-5 | ProvenanceRecord present + `model_domain: "1+1D_toy"` flagged for 0νββ |
