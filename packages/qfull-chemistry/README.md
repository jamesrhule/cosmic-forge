# `qfull-chemistry`

Quantum-chemistry domain plugin for QCompass. Implements the
`qcompass_core.Simulation` protocol so callers route molecular
electronic-structure problems (H₂/STO-3G FCI, LiH/6-31G DMRG,
N₂/cc-pVDZ CCSD(T), FeMoco-toy 54e/54o) through three execution
paths:

| Path | Backend | Module | Extra |
|---|---|---|---|
| Classical reference (HF / FCI / CCSD(T) / DMRG) | PySCF + block2 | `classical.py` | `[chem]` |
| Sample-then-Diagonalise (SQD) | Qiskit + Aer + qiskit-addon-sqd | `quantum_sqd.py` | `[sqd]` |
| Dice SHCI | qiskit-addon-dice-solver (Linux only) | `quantum_dice.py` | `[dice]` |

Every quantum result is paired with a classical reference computed
on the same machine; the resulting `ProvenanceRecord` carries the
`classical_reference_hash` so audits can attribute every output to
its inputs. FeMoco-toy is the documented exception — no classical
reference is feasible, so the hash is recorded as `"unavailable"`
and a `provenance_warning` is set.

## Boundary

This package MUST NOT import from `ucgle_f1` or any other `qfull_*`
sibling. CI enforces with both a `grep` guard and
`tests/test_boundary.py`. Cross-domain coupling flows exclusively
through `qcompass_core` protocols.

## Quick start

```bash
pip install qfull-chemistry[chem,sqd]

python -c "
from qcompass_core import Manifest, BackendRequest
from qcompass_core.registry import get_simulation
from qfull_chem.manifest import load_instance

problem = load_instance('h2')
sim = get_simulation('chemistry')()
manifest = Manifest(
    domain='chemistry',
    version='1.0',
    problem=problem.model_dump(),
    backend_request=BackendRequest(kind='auto'),
)
instance = sim.prepare(manifest)
backend = None  # the chemistry path resolves the backend internally
result = sim.run(instance, backend)
print('classical:', result.classical_energy)
print('quantum:', result.quantum_energy)
"
```

## Reference manifests

`src/qfull_chem/instances/` ships four YAML manifests:
`h2.yaml`, `lih.yaml`, `n2.yaml`, `femoco_toy.yaml`. Load them with
`qfull_chem.manifest.load_instance("h2")` etc.

## Audit

Per-domain audit lives at `src/qfull_chem/audit/`:

| Check | Test | Runs when |
|---|---|---|
| S-chem-1 | H₂/STO-3G FCI within 1e-8 Ha (classical) | `[chem]` installed |
| S-chem-2 | LiH/6-31G DMRG within 1 mHa | `[chem]` installed (with block2) |
| S-chem-3 | N₂/cc-pVDZ CCSD(T) within 1.6 mHa | `[chem]` installed |
| S-chem-4 | H₂ SQD on Aer recovers FCI to 1e-6 Ha | `[chem,sqd]` installed AND non-Darwin |
| S-chem-5 | ProvenanceRecord present + classical_reference_hash recorded | always |

Cross-platform note: `qiskit-addon-dice-solver` ships only on Linux,
so the `dice` extra is gated on `sys_platform == 'linux'`. Tests
that exercise Dice carry both `pytest.importorskip` and
`skipif(platform.system() == "Darwin")`. S-chem-4 runs SQD only and
is cross-platform.

## Layout

```
src/qfull_chem/
├── manifest.py         # ChemistryProblem + load_instance
├── classical.py        # HF / FCI / CCSD(T) / DMRG dispatcher
├── quantum_sqd.py      # qiskit-addon-sqd path (lazy import)
├── quantum_dice.py     # qiskit-addon-dice-solver (Linux only)
├── sim.py              # ChemistrySimulation orchestrator
├── instances/*.yaml    # H₂, LiH, N₂, FeMoco-toy
└── audit/              # S-chem-1 .. S-chem-5 pytest files
```

## Tests

```bash
uv run --package qfull-chemistry pytest -q
mypy --strict src/qfull_chem
```
