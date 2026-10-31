# `qfull-hep`

High-energy / lattice-gauge domain plugin for QCompass. Module:
`qfull_hep`.

## Domains

- Schwinger model (1+1D QED): chiral condensate, string tension.
- Z_N lattice gauge theory: structural plumbing only at Phase-1.
- Toy SU(2) gauge: structural plumbing only at Phase-1.

## Backends

| Path | Backend | Module | Extra |
|---|---|---|---|
| Classical reference (Schwinger ED) | numpy / scipy.sparse | `classical.py` | base |
| MPS reference (Schwinger ≥ 30 sites) | quimb tensor networks | `classical.py` | `[classical]` |
| IBM Heron (digital) | qiskit-ibm-runtime | `quantum_ibm.py` | `[ibm]` |
| IonQ Forte | amazon-braket-sdk | `quantum_ionq.py` | `[ionq]` |
| SC-ADAPT-VQE (Schwinger) | scadapt-vqe (Farrell et al. 2024) | `scadapt_vqe/` | research vendoring |

## SC-ADAPT-VQE vendoring note

PROMPT 5 §B asks us to "vendor the minimal Python version under
`src/qfull_hep/scadapt_vqe/`". The Phase-1 implementation ships a
**stub module** that documents the upstream reference
(arXiv:2401.04188, Farrell et al. 2024) and lazy-imports any
candidate package named `scadapt_vqe`. Vendoring the actual code
needs a license review (research-code IP) and is left for a
follow-up that goes through the `physics-reviewed` PR label.

## Boundary

This package MUST NOT import from `ucgle_f1` or any other `qfull_*`
sibling.

## Audit (S-hep-1..5)

| Check | Description |
|---|---|
| S-hep-1 | Schwinger 1+1D L=4 chiral condensate matches lattice exact-diag |
| S-hep-2 | String tension scales linearly in inter-charge distance for Schwinger L=6 |
| S-hep-3 | Anomaly-inflow consistency: total chiral charge change = topological charge |
| S-hep-4 | Classical-MPS agreement for L≥10 (skipped without quimb) |
| S-hep-5 | ProvenanceRecord present + classical_reference_hash recorded |
