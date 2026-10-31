# `qfull-amo`

Neutral-atom Rydberg / cold-atom domain plugin for QCompass. Module:
`qfull_amo`.

## Domains

- Rydberg-blockade ground states on small arrays (≤ 20 atoms) via
  exact diagonalisation.
- Maximum independent set (MIS) toy problems — adiabatic schedule.

## Backends

| Path | Backend | Module | Extra |
|---|---|---|---|
| Classical exact-diag | numpy / scipy.sparse | `classical.py` | base |
| Classical NQS | netket | `classical.py` | `[classical]` |
| Digital | bloqade (Julia/Python) | `quantum_bloqade.py` | `[bloqade_digital]` |
| Analog | bloqade-analog (QuEra Aquila via Braket) | `quantum_analog.py` | `[bloqade_analog]` |
| Pasqal | pulser | `quantum_pulser.py` | `[pasqal]` |

## Boundary

Must NOT import from `ucgle_f1` or any other `qfull_*`.

## Audit (S-amo-1..5)

| Check | Description |
|---|---|
| S-amo-1 | Rydberg ground-state energy lies in physical band for L ≤ 12 |
| S-amo-2 | MIS toy problem: optimal independent set is the global ground state |
| S-amo-3 | Adiabatic schedule fidelity ≥ 0.95 for L=4 reference schedule |
| S-amo-4 | Classical-NQS path skipped cleanly when netket absent |
| S-amo-5 | ProvenanceRecord present + classical_reference_hash recorded |
