# QCompass: Domain-Pluggable Shell Around UCGLE-F1

This plan operationalizes Sections 4–6 and Phase 1 of the assessment. Goal: keep the audited UCGLE-F1 cosmology pipeline frozen and byte-identical, and add the minimum architectural scaffolding so other physics domains (chemistry, condensed matter, HEP, nuclear, AMO, gravity, statmech) can be added later as opt-in plugins without ever touching the core.

This is a **shell + contracts** phase. We are not implementing any quantum backend, chemistry solver, or new science. We are building the seams.

---

## Scope (in)

1. **Domain registry**: a typed plugin contract (`Simulation` protocol equivalent in TS) that the existing leptogenesis simulator implements as `qcompass.cosmology.ucglef1`.
2. **Manifest envelope**: a `{ domain, version, problem, backendRequest }` Pydantic-style Zod schema; UCGLE-F1's existing `RunConfig` becomes the `problem` payload of the `cosmology.ucglef1` domain — with a backwards-compatible adapter so all existing fixtures, persisted rows, and routes keep working unchanged.
3. **Stub modules** (typed interfaces + no-op implementations + fixtures):
   - `M11` Hamiltonian Registry — schema-only, no instances yet.
   - `M12` Resource Estimator — interface + Azure-QRE-shaped result type, returns "n/a, classical" for cosmology.
   - `M13` Classical Reference — interface; cosmology returns its own audit as the reference.
   - `M14` Backend Router — interface, single route: `cosmology → cpu-classical`.
   - `M15` Benchmark Suite — namespace stub with the existing UCGLE-F1 benchmarks registered as the cosmology entry.
4. **UI**: a non-breaking domain selector chip in the header. Only `Cosmology · UCGLE-F1` is enabled; other domains appear disabled with a "Phase 2" tooltip. Existing Configurator stays the default landing experience.
5. **Provenance record type**: optional `ProvenanceRecord` field on results (nullable for cosmology), so future quantum-derived claims can attach `(classical_reference, resource_estimate, device_calibration_hash, error_mitigation_config)`.
6. **Feature flag**: new `FEATURES.domainsRegistry` (default `false`) — when off, nothing in the UI changes.
7. **Audit doc**: extend `docs/audit.md` with a "QCompass shell" section describing the isolation contract and the rule that S1–S15 only reads cosmology outputs.

## Scope (out)

- No quantum SDKs (CUDA-Q, Qiskit, Cirq, Bloqade, etc.) — those are Phase 2.
- No new domain solvers, no chemistry, no lattice code, no Hamiltonian instances.
- No changes to M1–M7, S1–S15, the existing simulator service contract, the persisted DB schema, or any fixture hash.
- No backend cutover changes, no auth changes, no new edge functions.
- No rebrand of the user-facing app yet (codename internal only). The header still reads "UCGLE-F1 Workbench" until the user approves a rename.

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│  TanStack Start UI                                           │
│   • Header: <DomainSelector />  (gated by domainsRegistry)   │
│   • Default route /  → cosmology.ucglef1 Configurator        │
├──────────────────────────────────────────────────────────────┤
│  src/lib/domains/                  ← NEW                     │
│   • registry.ts       (DomainPlugin map, lookup, list)       │
│   • types.ts          (Simulation, Manifest, Provenance)     │
│   • cosmology.ucglef1.ts  (adapter over existing simulator)  │
├──────────────────────────────────────────────────────────────┤
│  src/lib/qcompass/                 ← NEW (stubs)             │
│   • hamiltonianRegistry.ts  (M11)                            │
│   • resourceEstimator.ts    (M12)                            │
│   • classicalReference.ts   (M13)                            │
│   • backendRouter.ts        (M14)                            │
│   • benchmarkSuite.ts       (M15)                            │
├──────────────────────────────────────────────────────────────┤
│  EXISTING — UNCHANGED                                        │
│   • src/services/{simulator,visualizer,assistant,artifacts}  │
│   • src/types/domain.ts (RunConfig, RunResult, AuditReport)  │
│   • src/lib/persistence.ts, supabase tables, RLS policies    │
│   • S1–S15 audit, M1–M7 module ids, fixture bytes            │
└──────────────────────────────────────────────────────────────┘
```

The cosmology adapter is the only place the registry knows about UCGLE-F1; it forwards `prepare/run/validate` straight to `services/simulator.ts`. Nothing in `services/` imports anything from `src/lib/domains/` or `src/lib/qcompass/` — coupling is one-way.

---

## Files

**New**
- `src/lib/domains/types.ts` — `DomainId`, `DomainPlugin`, `Manifest<T>`, `Simulation<T,R>`, `ProvenanceRecord`, `DomainCapability`.
- `src/lib/domains/registry.ts` — `registerDomain`, `getDomain`, `listDomains` (in-memory; populated at module load).
- `src/lib/domains/cosmology.ucglef1.ts` — adapter; registers itself with id `cosmology.ucglef1`, capability `{ classical: true, quantum: false }`, audit suite `S1–S15`.
- `src/lib/qcompass/hamiltonianRegistry.ts` — `HamiltonianFormat` enum (`fcidump | lqcd_hdf5 | spin_json | majorana_sparse | cosmology_runconfig`) + empty registry.
- `src/lib/qcompass/resourceEstimator.ts` — `estimate(manifest): ResourceEstimate` interface; cosmology impl returns `{ kind: "classical", note: "ODE+Boltzmann" }`.
- `src/lib/qcompass/classicalReference.ts` — `getReference(manifest)` interface; cosmology returns its own audit report.
- `src/lib/qcompass/backendRouter.ts` — `route(manifest): BackendChoice`; single rule `cosmology.* → cpu-classical`.
- `src/lib/qcompass/benchmarkSuite.ts` — re-exports existing UCGLE-F1 benchmarks tagged with `domain: "cosmology.ucglef1"`.
- `src/components/domain-selector.tsx` — header chip; lists registered domains, only `cosmology.ucglef1` enabled.

**Edited**
- `src/config/features.ts` — add `domainsRegistry: boolean` (default `false`, env-overridable via `VITE_DOMAINS_REGISTRY`).
- `src/types/domain.ts` — add optional `provenance?: ProvenanceRecord` to `RunResult` (nullable; cosmology never sets it). No other field changes.
- `src/routes/__root.tsx` or `src/routes/index.tsx` — mount `<DomainSelector />` in the header (behind the flag).
- `docs/audit.md` — add "QCompass shell isolation contract" section.

**Not touched**
- `src/services/*`, `src/lib/persistence.ts`, `src/integrations/supabase/*`, `supabase/migrations/*`, all S1–S15 logic, all M1–M7 module strings, `RunConfig`, `eta_B` validators, every fixture file under `public/fixtures/`.

---

## Acceptance criteria

1. With `FEATURES.domainsRegistry = false` (default), the app is **visually and functionally identical** to before this change. No new chips, no new routes, no fixture changes.
2. With the flag on, the header shows a domain selector chip listing one enabled entry (`Cosmology · UCGLE-F1`) and seven disabled entries with "Phase 2" tooltips.
3. `getDomain("cosmology.ucglef1").run(manifest)` produces a `RunResult` byte-identical to the existing `services/simulator.ts` path (the adapter is a pure delegation).
4. `tsc --noEmit` and the production build pass.
5. No file under `src/services/` imports from `src/lib/domains/` or `src/lib/qcompass/`.
6. `docs/audit.md` contains the isolation contract clause and the rule "S1–S15 reads cosmology outputs only".

---

## Naming

Internal codename `QCompass` (per Section 6) lives only in code comments, the audit doc, and the disabled-domain tooltips. The user-facing product name **stays "UCGLE-F1 Workbench"** in this phase. A rename to `QCompass` (with UCGLE-F1 preserved as `qcompass.cosmology.ucglef1`) is a separate decision; flag it for a future turn.

---

## Out-of-band notes (for later phases, not implemented now)

- Phase 2 will add the first real domain plugin (`qfull-chemistry` per the assessment) behind its own feature flag and its own S-Q audit suite.
- QDMI/QRMI adoption, CUDA-Q wiring, Azure QRE integration, and per-domain DB tables are all deferred until at least one quantum experiment template is needed.
- The `ProvenanceRecord` field is reserved now so adding it later is non-breaking for stored `RunResult` rows.

If this matches the intent, approve and I'll implement Phase 1 exactly as scoped above. If you'd rather start with a real domain plugin (e.g., a chemistry stub that loads an FCIDUMP fixture but doesn't solve it) instead of pure scaffolding, say so and I'll re-scope before building.
