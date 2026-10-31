# QCompass: a multi-domain quantum + classical research workbench

*arXiv preprint skeleton — PROMPT 10 v2 §E. Sectioning + section
prompts only; numerical claims land when the Phase-3 verdict
flips each domain to DELIVERED.*

## Abstract

QCompass is a vendor-neutral protocol layer + router + benchmark
harness + frontend visualizer for quantum + classical research.
The reference cosmology kernel (UCGLE-F1) reproduces the
Kawai-Kim 2024 V1-V8 recovery suite at the frozen
`ucglef1-v1.0.0` tag. Seven additional domain plugins (chemistry,
condensed matter, high-energy physics, nuclear, AMO, gravity,
statistical mechanics) follow the same protocol contract, share
the cost-aware router and the bundled-manifest leaderboard, and
flow into a single particle-research-aware visualizer.

## 1. Introduction

- Motivation: today's quantum runs scatter across vendor SDKs
  with incompatible provenance fields; researchers cannot
  reproduce a peer's run without rebuilding the harness.
- Contribution: (1) a single Pydantic protocol every plugin
  satisfies, (2) a cost-aware router with per-tenant budgets,
  (3) a Phase-3 descope-or-commit verdict pipeline that prevents
  silent abandonment.

## 2. Architecture

- 2.1 Protocol layer (`qcompass-core`)
- 2.2 Router + free-tier preference
- 2.3 Bench + bundled manifests
- 2.4 Visualization (`cosmic_forge_viz`) + per-domain frame schemas
- 2.5 Auth + tenancy
- 2.6 Observability + Prometheus metrics

## 3. Domains

For each domain: kinds, classical reference, per-domain audit
contract. Tables of pinned numerical results (η_B for cosmology,
chiral condensate for HEP, etc.) cite the per-domain references
in the bibliography.

## 4. Phase-3 verdict pipeline

The four delivery criteria (≥3 reproducible classical_reference_
hash records, quantum advantage at the same wallclock, peer-
reviewed citation, audit green ≥30 days). Failure mode: auto-PR
moves the source tree to `research/packages/` while preserving the
audit trail.

## 5. Reproducibility

- Freeze contract on `backend/audit/physics/`.
- Provenance sidecars per run.
- Per-tenant budget enforcement.

## 6. Limitations & future work

- The fault-tolerant resource estimator falls back to a closed-form
  Litinski approximation when the Azure RE / QREChem / TFermion
  wheels are absent.
- Live cloud runs require credentials the bench harness does not
  bundle.

## References

See `references.bib`. Per-domain entries match the verdict
pipeline's `qcompass-<domain>` namespace.

---

*Compile: this preprint will be rendered to LaTeX via Pandoc when
the `release-please` workflow ships v1.0.0.*
