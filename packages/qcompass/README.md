# `qcompass` — meta-package

PROMPT 10 v2 §E. `pip install qcompass` pulls every DELIVERED
qfull-* plugin plus the qcompass-core / qcompass-router /
qcompass-bench layer. Use this when you want a one-shot install
of the entire workbench. Per-domain installs (`pip install
qfull-chemistry`) remain available for slimmer footprints.

## Quick start

```python
from qcompass import (
    Manifest, BackendRequest,
    get_simulation, list_domains,
    run_benchmark_suite,
    run_verdict,
)

print(list_domains())            # ≥8 domains after PROMPT 9 v2

sim_cls = get_simulation("chemistry")
manifest = Manifest(
    domain="chemistry", version="1.0",
    problem={"molecule": "H2", "basis": "sto-3g"},
    backend_request=BackendRequest(kind="classical"),
)
result = sim_cls().run(sim_cls().prepare(manifest), backend=None)

# Particle-suite benchmark across hep + nuclear bundled fixtures.
report = run_benchmark_suite("particle", providers=["local_aer"])

# Phase-3 descope-or-commit verdict.
verdict = run_verdict(cutoff_days=90)
```

## Optional extras

- `qcompass[ibm]` — qiskit + qiskit-aer + qiskit-ibm-runtime
- `qcompass[azure]` — azure-quantum
- `qcompass[tn]` — quimb + tensornetwork
- `qcompass[chem]` — pyscf
- `qcompass[ft]` — placeholder (azure-quantum + QREChem +
  TFermion ride the `[azure]` extra today; the `[ft]` slot stays
  reserved for the Microsoft Quantum + IonQ FT toolchains as they
  land)

## DELIVERED domains (Phase-3 verdict cut)

The list below is updated by the monthly `phase3-verdict` workflow
when a domain promotes to 1.0:

- chemistry, condmat, amo, hep, nuclear, gravity, statmech
- cosmology (frozen at `ucglef1-v1.0.0`)
