# `qcompass-router`

Cost-aware backend router for the QCompass workspace. Module:
`qcompass_router`. Promoted from skeleton in PROMPT 6A; PROMPT 6B
adds live pricing fetchers, the calibration drift cache, transform
adapters, and the full A-router-1..6 audit.

## Surface (PROMPT 6A)

```python
from qcompass_router import (
    Router, RouterRequest, RoutingDecision,
    pricing_stub, list_providers,
)

router = Router()                    # auto-discovers every adapter
decision = router.decide(RouterRequest(
    circuit_qasm="...",
    shots=4096,
    budget_usd=0.0,                  # → local_aer
))
print(decision.provider, decision.backend, decision.cost_estimate_usd)
```

`RouterRequest` is the router's own request envelope. It is
INTENTIONALLY a separate type from `qcompass_core.BackendRequest`
(the existing manifest envelope) — the qcompass-core type stays
byte-stable so every qfull-* plugin keeps working unchanged. The
router consumes `RouterRequest` directly; downstream calls into
qcompass-core's M14 router still use `BackendRequest`.

## Boundary

This package MUST NOT import from `ucgle_f1` or any `qfull_*`. The
parametric CI step in `.github/workflows/ci.yml` (with empty
`boundary_module` for `qcompass-*` rows) enforces it, plus
`tests/test_boundary.py` walks the source tree on every run.

## Provider adapters

Nine soft-imported adapters under `src/qcompass_router/providers/`.
Each defines a class that satisfies `ProviderAdapter` (ABC) and
guards SDK imports inside `is_available()`:

| Adapter | Kind | Optional extra |
|---|---|---|
| `local_aer` | local | `[ibm]` |
| `local_lightning` | local | `[lightning]` |
| `ibm` | cloud-sc | `[ibm]` |
| `braket` | cloud-other | `[braket]` |
| `azure` | cloud-other | `[azure]` |
| `ionq` | cloud-ion | `[ionq]` |
| `iqm` | cloud-sc | `[iqm]` |
| `quera` | cloud-neutral-atom | `[quera]` |
| `pasqal` | cloud-neutral-atom | `[pasqal]` |

Importing the package without any optional SDK installed
succeeds; calling a missing SDK raises a clear hint via the
adapter's own helpers.

## Stub pricing

`fixtures/pricing_seed.yaml` ships seed values per provider; the
PROMPT 6A `pricing_stub.estimate(provider, backend, shots)`
returns the static dollar cost. PROMPT 6B replaces this with the
live pricing module + on-disk cache + SSL-pinned fetchers.

## Audit (PROMPT 6A)

Five tests under `tests/`:

- `test_provider_soft_import.py` — every adapter importable
  without its SDK; `is_available()` returns False with no creds.
- `test_router_local_aer.py` — `budget=0` resolves to
  `local_aer`.
- `test_router_real_hw_no_budget.py` — `budget=0,
  require_real_hardware=True` raises `BudgetExceeded`.
- `test_router_paid_cheapest.py` — mocked pricing where IBM Heron
  is cheaper than IonQ Forte; `budget=$50` selects Heron.
- `test_router_preferred_filter.py` — `preferred_providers=["ionq"]`
  excludes IBM even when it would otherwise win.

Plus `test_boundary.py` for the import guard.

## PROMPT 6B preview

- Live pricing fetchers (one per provider) behind an SSL-pinned
  httpx client. Cached at `~/.cache/qcompass/pricing/`.
- Calibration drift cache (SQLite at
  `~/.cache/qcompass/calibration.sqlite`); 7-day median + 3σ
  rejection raises `CALIBRATION_DRIFT`.
- Transform stack: `qiskit-addon-aqc-tensor / mpf / obp /
  cutting`. Each application adds a `TransformRecord` to
  `RoutingDecision.transforms_applied`, which the calling
  `Simulation.run()` propagates into
  `ProvenanceRecord.error_mitigation_config`.
- Audit suite `A-router-1..6` enforcing the full contract.
