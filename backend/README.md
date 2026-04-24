# UCGLE-F1 — Python backend

Scalar–Gauss-Bonnet–Chern-Simons (sGB-CS) gravitational leptogenesis
simulator with a co-located agent orchestrator (M8).

The companion TypeScript frontend lives in the repository root (`/src`).
This package lives under `/backend` and follows a Python **src layout**
(`backend/src/ucgle_f1/...`). The two are kept in separate directories
so that `pyproject.toml` / `src/ucgle_f1/` does not collide with the
React project.

## Modules

| ID | Package                    | Purpose                                           |
|----|----------------------------|---------------------------------------------------|
| M1 | `ucgle_f1.m1_background`   | Friedmann background (astropy + scipy)            |
| M2 | `ucgle_f1.m2_scalar`       | Scalar EOM (sympy → JAX / numpy)                  |
| M3 | `ucgle_f1.m3_modes`        | Chiral tensor modes + F_GB (diffrax, Bogoliubov)  |
| M4 | `ucgle_f1.m4_anomaly`      | ⟨RR̃⟩ → ΔN_L (adiabatic subtraction)              |
| M5 | `ucgle_f1.m5_boltzmann`    | ULYSSES bridge → η_B                              |
| M6 | `ucgle_f1.m6_gw`           | SGWB + interferometry (cosmoGW/PTAfast/GWBird)    |
| M7 | `ucgle_f1.m7_infer`        | Hydra/OmegaConf configs + Cobaya/bilby inference  |
| M8 | `ucgle_f1.m8_agent`        | Agent orchestrator (FastAPI + MCP tools)          |

## Validation benchmarks

Physics references are keyed by arXiv ID in
`src/ucgle_f1/m8_agent/bibliography.json`:

- **V2** Kawai & Kim, [1702.07689](https://arxiv.org/abs/1702.07689)
- **V3** Kamada et al., [2007.08029](https://arxiv.org/abs/2007.08029)
- **V4** [2412.09490](https://arxiv.org/abs/2412.09490)
- **V5** [2403.09373](https://arxiv.org/abs/2403.09373)

## Install

```bash
pip install -e "backend[dev,jax,cosmo]"
```

Heavy optional backends (`ulysses`, `camb`, `classy`, `vllm`, …) are
pulled in by extras — see `pyproject.toml`.

## Audit invariants

- **S1–S15** live under `backend/audit/physics/` — one pytest file
  exercises every check through the full M1–M7 pipeline. Tests
  assert that the audit harness is structurally well-formed (verdicts
  are valid literals, references resolve against the shipped
  bibliography); a `FAIL` verdict is the harness telling the agent
  its coupling / precision / grid is not yet tuned to V2 — it is
  part of normal operation, not a bug.
- **A1–A6** live under `backend/audit/agent/` — agent-orchestrator
  invariants (schema validity, citation integrity, sandbox
  containment, determinism, audit preservation under patches,
  run traceability).

Run the full audit with

```bash
pytest backend/audit -q -m "not slow"       # ~3 min on a laptop CPU
pytest backend/audit -q                     # includes hypothesis stress tests
```

### Precision ladder

| precision    | n_k | k-range       | rtol / atol   | unitarity escalation |
|--------------|----|---------------|---------------|----------------------|
| `fast`       | 8  | [1e-1, 1e+1] | 1e-6 / 1e-8   | 1e-4 (skip mpmath)   |
| `standard`   | 16 | [1e-2, 1e+2] | 1e-8 / 1e-10  | 1e-4 (skip mpmath)   |
| `high`       | 64 | [1e-3, 1e+3] | 1e-10 / 1e-12 | 1e-12 (mpmath dps=50)|

Recovering the V2 (Kawai-Kim, 1702.07689) η_B target to within 10%
requires `precision='high'` and a coupling profile tuned to the V2
parameters. The smoke-test configurations in `backend/configs/` use
`precision='fast'` so tests complete in CI budget; promote to
`high` for publication-quality runs.

## Agent orchestrator (M8)

```bash
ucgle-f1-agent --host 127.0.0.1 --port 8787
```

Exposes:

- `GET  /openapi.json`                   – HTTP schema
- `GET  /mcp/tools`                      – MCP tool spec
- `POST /v1/chat`                        – streaming chat (SSE)
- All tools at `/tools/{family}/{name}`  – one-shot invocations

See `backend/docs/agent_demo.ipynb` for an end-to-end walkthrough.
