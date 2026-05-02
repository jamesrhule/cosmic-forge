# QCompass — final acceptance report (PROMPT 11)

**Verdict:** **GO-WITH-CAVEATS**

The full v2 build sequence (PROMPTs 0-10) plus the integration
verification (PROMPT 11) is landed on
`claude/ucgle-f1-agent-simulator-agRxR`. Every blocking DoD bullet
in Sections 1-11 is met or DEFERRED-with-justification. The
freeze contract on `backend/audit/physics/` is intact.

The CAVEATS are all "documented sandbox limits" — they do not
indicate a code-level regression:

1. The Lovable handoff described in PROMPT 11's CONTEXT block is
   broader than what's actually on disk (no `services/qcompass/
   {auth,http,scans,visualizer,literature,verdict,runs}.ts`,
   empty per-domain `runs/*.json` directories beyond chemistry,
   no `MetricsTile`). The integration verification is scoped to
   the surface that exists today; missing pieces are tracked in
   `docs/qcompass/lovable-handoff-mismatches.md`.
2. Playwright + `bunx playwright test` cannot run in-sandbox (no
   `npm install --save-dev @playwright/test`). The spec scaffolding
   ships at `e2e/{cosmology-byte-identity,chemistry-h2-flow}.spec.
   ts` and runs as soon as the install lands.
3. PyPI / GHCR / mkdocs publish trigger only on `release-please`
   PR merge → tag, which the sandbox cannot execute.
4. The UCGLE-F1 V2 calibration (PROMPT 10 §C) is a process gate:
   the `physics-reviewed` PR template + the existing drift-alarm
   label-enforcement workflow are in place, but the actual
   calibration bump requires a human reviewer with V1-V8 recovery
   data and is intentionally out of scope for this PR.

---

## Per-section status

| Section | Description | Status | Evidence |
|---|---|---|---|
| 1 | qcompass-core + freeze infra | ✅ PASS | `physics_dir_hash 42805c73…f8e92dd` intact; drift-alarm CI + golden.lock present (PROMPT 0 v2). |
| 2 | qcompass-bench (≥16 fixtures across ≥6 domains) | ✅ PASS | bundled-manifest registry + 16 fixtures + soft-import runners (PROMPT 1 v2). |
| 3 | cosmic-forge → Simulation adapter | ✅ PASS | `backend/src/ucgle_f1/adapters/qcompass.py` + provenance sidecar; A1-A6 byte-stable (PROMPT 2 v2). |
| 4 | qfull-chemistry / qfull-condmat / qfull-amo | ✅ PASS | 3 plugins + S-chem/S-cm/S-amo audits (PROMPT 3 v2). |
| 5 | qfull-hep + qfull-nuclear (particle research) | ✅ PASS | particle_obs schema + Schwinger 5%-band + 0νββ LNV signature + suite="particle" alias (PROMPT 5 v2). |
| 6 | qcompass-router production | ✅ PASS | PricingEngine + Cost + CalibrationCache + drift_score + transforms ladder + A-router-1..6 (PROMPTs 6 + 7 v2). |
| 7 | cosmic-forge visualizer backend | ✅ PASS (live latency DEFERRED) | cosmic_forge_viz package + 6 + 2 = 8 frame schemas + WS / SSE / REST routes; 26 tests (PROMPT 7 v2). |
| 8 | M8 HTTP surface + scans + A7 audit | ✅ PASS | `/api/qcompass/*` + `/ws/qcompass/*` + `/api/scans/*`; 11 A7 tests (PROMPT 8 v2). |
| 9 | qfull-gravity + qfull-statmech + FT compilation + FeMoco / Schwinger templates | ✅ PASS | 9 domains in registry; FaultTolerantPlan matches Azure RE pinned vectors; learned-Hamiltonian guard BLOCKS (PROMPT 9 v2). |
| 10A | Auth + tenancy | ✅ PASS | `auth.py` + `qcompass_routes.py` Depends + `/v1/chat` Depends; 11 A8 tests (PROMPT 10 v2). |
| 10B | Observability + /metrics | ✅ PASS | `observability.py` + Prometheus registry + 9 A9 tests. |
| 10C | UCGLE-F1 V2 calibration | ⚠ PROCESS-GATE ONLY | PR template `.github/PULL_REQUEST_TEMPLATE/physics-reviewed.md` + drift-alarm label enforcement; freeze unchanged. |
| 10D | Phase-3 verdict pipeline | ✅ PASS | `phase3_verdict.py` + CLI + 8 tests + monthly cron workflow + sample verdict fixture. |
| 10E | Release scaffolding | ✅ PASS (publish DEFERRED) | `packages/qcompass/` + `docker/Dockerfile.{cpu,cuda12}` + `mkdocs.yml` + `release-please.yml`. |
| 11A | Lovable contract walk + round-trip | ✅ PASS | `docs/qcompass/lovable-handoff-mismatches.md` + `backend/tests/test_lovable_contract.py` (8 passed, 4 skipped for empty domain dirs). chemistry.ts JSDoc reconciled. |
| 11B | Playwright end-to-end smoke | ⏸ DEFERRED | sandbox lacks `npm install`; specs at `e2e/` ready to run. |
| 11C | Feature-flag matrix | ⏸ DEFERRED for live; ✅ STATIC | static contract test holds across the flag matrix; cosmology byte-identity spec waits on Playwright. |
| 11D | Acceptance report | ✅ PASS | this file. |

---

## Freeze contract

| Anchor | Value |
|---|---|
| `backend/audit/golden.lock.physics_dir_hash` | `42805c73538df5eb0f9eb109ead9a541253d5371d71eac5ea04be0ffaf8e92dd` |
| Drift-alarm workflow | `.github/workflows/ucglef1-drift-alarm.yml` |
| Mutation gate | `physics-reviewed` PR label (CI enforces) |
| PR template | `.github/PULL_REQUEST_TEMPLATE/physics-reviewed.md` |
| Status | **INTACT** across PROMPTs 0-11. |

---

## Test counts (this commit)

```
backend/audit -q -m "not slow"          81 passed (50 v1 + 11 A7
                                                   + 11 A8 + 9 A9)
                                        1 deselected
backend/tests -q                        59 passed, 3 skipped, 1 xfailed
                                          • cosmic_forge_viz: 26 passed
                                          • test_lovable_contract: 8 passed,
                                            4 skipped (empty domain dirs)
                                          • 1 xfail = V2 calibration parked
packages -q -m "not slow"               204 passed, 1 skipped
                                        (was 178 at PROMPT 4 v2)
```

Per-domain audit suites green:
- S1-S15 (cosmology) — frozen at `ucglef1-v1.0.0`.
- S-chem-1..5, S-cm-1..5, S-amo-1..5 (PROMPT 3 v2).
- S-hep-1..6, S-nuc-1..6 (PROMPT 5 v2).
- S-grav-1..6 incl. BLOCKING provenance-warning gate (PROMPT 9 v2).
- S-stat-1..5 (PROMPT 9 v2).
- A-router-1..6 (PROMPTs 6 + 7 v2).
- A1..A9 backend agent audits (PROMPTs 0 + 8 + 10 v2).

---

## Lovable contract — exhaustive walk

Tracked in `docs/qcompass/lovable-handoff-mismatches.md`. Summary:

- **Present services** (`src/services/qcompass/`):
  `chemistry.ts`, `manifest.ts`, `manifestSchema.ts` — every
  `Backend:` JSDoc reconciled against the M8 `/api/qcompass/
  domains/chemistry/...` paths the SDK already calls.
- **Present components** (`src/components/visualizer/panels/`):
  16 TSX panels across 8 domain folders incl. the v2 mandated
  `ParticleObservablesTable`, `ModelDomainBadge`,
  `ProvenanceWarningBanner`.
- **Present fixtures** (`public/fixtures/`):
  - `chemistry/runs/*.json` (4 runs) — round-trips through
    `qcompass_core.Manifest` cleanly.
  - `visualizations/*.json` (15 timelines) — generated by the
    cosmic_forge_viz baker.
  - `verdict/sample-verdict.{yaml,md}` — generated by a real
    `phase3_verdict.run_verdict()` invocation in this PR.
  - `literature/lattice-qcd-references.json` — anchored entries
    for the HEP `ParticleObservablesTable` "compare to literature"
    affordance.
- **Absent (logged):** `services/qcompass/{auth,http,scans,
  visualizer,literature,verdict,runs}.ts`, fixture directories
  for non-chemistry domains, `MetricsTile`. The
  `test_lovable_contract.py` suite parametrises by glob so every
  absent dir cleanly skips today and grows real assertions when
  Lovable lands those fixtures.

---

## Integration smoke — what's actually verified

| Surface | Verification | Status |
|---|---|---|
| `qcompass_core.Manifest.model_validate(<chemistry fixture>)` | round-trip 4 fixtures | ✅ green |
| `qcompass_core.ProvenanceRecord.model_validate(<chemistry fixture>.provenance)` | 4 fixtures | ✅ green |
| `chemistryService(client).submit(...)` → `POST /api/qcompass/domains/chemistry/runs` | A7 audit | ✅ green |
| WS `/ws/qcompass/domains/{domain}/runs/{run_id}/visualization` envelope round-trip | A7 audit | ✅ green |
| Auth gate on `/api/qcompass/*` | A8 audit | ✅ green |
| Tenant budget gate on `PricingEngine.estimate(...)` | A8 audit | ✅ green |
| `/metrics` Prometheus endpoint | A9 audit | ✅ green |
| Phase-3 verdict CLI emits `verdict_report.{yaml,md}` | `test_phase3_verdict.py` | ✅ green |
| Drift-alarm + physics-reviewed gate | workflow inspection + freeze hash | ✅ green |
| Playwright cosmology byte-identity | DEFERRED until `npm install` available | ⏸ |
| Live PyPI install of `qcompass` meta-package | DEFERRED until release tag | ⏸ |

---

## Recommended next steps

1. **Land the rest of the Lovable handoff** the PROMPT 11
   CONTEXT described (full `services/qcompass/*` set, per-domain
   fixtures, `MetricsTile`). The contract test grows assertions
   automatically as the fixtures appear.
2. **Run Playwright** in CI once `npm install --save-dev
   @playwright/test` lands. The `e2e/cosmology-byte-identity.spec
   .ts` byte-identity gate exists but has never executed in the
   sandbox.
3. **Cut the first PyPI release** via the `release-please`
   workflow on the next push to `main`. The meta-package's
   per-package version manifest is at
   `.github/release-please-manifest.json`.
4. **Run the V2 calibration PR** through the `physics-reviewed`
   path once a reviewer with V1-V8 recovery data is available.
   The PR template captures every required line item.
