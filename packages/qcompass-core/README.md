# `qcompass-core`

Shared protocol layer for the QCompass workspace.

## Boundary

This package MUST NOT import from `ucgle_f1` or any `qfull_*`
sibling. CI enforces the boundary with a grep guard
(see `.github/workflows/ci.yml`).

Cross-domain plumbing (provenance envelopes, manifest schemas,
backend routing, classical reference adapters) lives here so every
`qfull-*` plugin can depend on a single stable contract.

## Public surface

| Symbol | Purpose |
|---|---|
| `Manifest`, `BackendRequest`, `ProvenanceRecord`, `ResourceEstimate` | Typed envelope (Pydantic v2). |
| `Simulation`, `QProvider`, `QBackend`, `QEstimator` | PEP 544 protocols. |
| `get_simulation`, `list_domains`, `register` | Plugin registry over `qcompass.domains` entry points. |
| `Router`, `get_backend`, `available_backends` | M14 backend routing. |
| `FCIDUMP`, `read_fcidump`, `SpinHamiltonian` | M11 Hamiltonian inputs. |
| `StubEstimator`, `AzureMicrosoftEstimatorAdapter`, `QREChemAdapter`, `TFermionAdapter` | M12 estimator adapters. |
| `PySCFAdapter`, `Block2Adapter`, `QuimbAdapter`, `IpieAdapter` | M13 classical reference adapters. |

## Built-in `null` plugin

```python
from qcompass_core import get_simulation, Manifest, BackendRequest

sim = get_simulation("null")()
manifest = Manifest(
    domain="null",
    version="1.0",
    problem={"label": "noop"},
    backend_request=BackendRequest(kind="classical"),
)
instance = sim.prepare(manifest)
```

The plugin is registered through the `qcompass.domains` entry-point
group; tests can also `register("name", cls)` programmatically.

## Optional extras

```bash
pip install qcompass-core[chem]      # PySCF + block2
pip install qcompass-core[tn]        # quimb tensor networks
pip install qcompass-core[afqmc]     # ipie AFQMC
pip install qcompass-core[ibm]       # qiskit + qiskit-aer + IBM runtime
pip install qcompass-core[azure]     # azure-quantum (Microsoft QRE)
pip install qcompass-core[research]  # vendored research adapters (TFermion, QREChem)
```

Adapters with absent extras raise `ResourceEstimationError` /
`ClassicalReferenceError` / `BackendUnavailableError` rather than
import-time failures, so callers can degrade gracefully.

## Tests

```bash
uv run --package qcompass-core pytest -q
mypy --strict src/qcompass_core
```
