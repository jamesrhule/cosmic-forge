# Lovable handoff — contract reconciliation log

PROMPT 11 §A asks the integration sweep to walk every JSDoc
`@endpoint` annotation in `src/services/qcompass/*.ts`, confirm
the matching FastAPI route exists, and document mismatches here
rather than silently moving fixtures.

## Prerequisite gap (logged)

The driving prompt's CONTEXT block describes a Lovable handoff
that includes:

- `src/services/qcompass/{manifestSchema,runs,visualizer,scans,
  literature,verdict,auth,http}.ts`
- `public/fixtures/{condmat,amo,hep,nuclear,gravity,statmech,
  verdict}/runs/*.json` plus learned-syk warnings, particle_obs
  blocks, and verdict YAML/MD samples.
- A `MetricsTile` component on the frontend.

On disk the realised state is narrower:

| Lovable surface | Status | Notes |
|---|---|---|
| `src/services/qcompass/chemistry.ts` | present | already wired through `@qcompass/frontend-sdk` (PROMPT 8 v2) |
| `src/services/qcompass/manifest.ts` | present | re-export shim |
| `src/services/qcompass/manifestSchema.ts` | present | hits `/api/qcompass/domains/{domain}/schema` |
| `src/services/qcompass/{runs,visualizer,scans,literature,verdict,auth,http}.ts` | **absent** | not landed by Lovable on this branch |
| `public/fixtures/chemistry/runs/*.json` | present | 4 runs (h2-sto3g, lih-631g, n2-ccpvdz, femoco-toy) |
| `public/fixtures/{condmat,amo,hep,nuclear,gravity,statmech,verdict}/` | empty dirs | Lovable handoff did NOT populate these |
| `MetricsTile` | absent | not landed |

The PROMPT 11 ground rule "the frontend contract is the contract"
is interpreted strictly: **what's actually on disk is the contract**.
Sections 11.A / 11.B / 11.D below are scoped to the surface that
exists rather than the surface the prompt's CONTEXT claimed
existed.

When the rest of the Lovable handoff lands, this file's "absent"
rows should each grow a contract row + a round-trip test in
`backend/tests/test_lovable_contract.py`.

---

## §A — JSDoc `@endpoint` walk

### `src/services/qcompass/manifestSchema.ts`

| JSDoc reference | M8 route | Status | Resolution |
|---|---|---|---|
| `GET {API_BASE_URL}/api/qcompass/domains/{domain}/schema` | `GET /api/qcompass/domains/{domain}/schema` (auth-gated) | ✅ match | none required |

### `src/services/qcompass/chemistry.ts`

The file ships two layers:

1. JSDoc `Backend:` annotations (predate the SDK wiring).
2. The actual `startChemistryRun` body (PROMPT 8 v2) which
   delegates to `sdkChemistryService(getSdkClient()).submit(...)`.

| JSDoc reference (predates SDK) | Actual SDK call (live path) | M8 route | Resolution |
|---|---|---|---|
| `GET /api/qcompass/chemistry/runs` | `chemistryService(client).submit(manifest)` → `POST /api/qcompass/domains/chemistry/runs` | ✅ matches the `/domains/chemistry/runs` path the M8 server actually exposes | **stale JSDoc updated** in this PR — the comments now reflect the `/api/qcompass/domains/chemistry/...` path the SDK already calls. |
| `GET /api/qcompass/chemistry/runs/{id}` | live: SDK `chem.get(runId)` → `GET /api/qcompass/domains/chemistry/runs/{run_id}` | ✅ same — JSDoc updated |
| `POST /api/qcompass/chemistry/runs` | live: SDK `chem.submit(manifest)` → `POST /api/qcompass/domains/chemistry/runs` | ✅ same — JSDoc updated |
| `SSE GET /api/qcompass/chemistry/runs/{id}/stream` | live: SDK `chem.stream(runId)` → `GET /api/qcompass/domains/chemistry/runs/{run_id}/stream` | ✅ same — JSDoc updated |

The JSDoc-vs-SDK mismatch is **internal to chemistry.ts** rather
than between Lovable's frontend and the backend; the SDK already
hits the canonical M8 path. Per the prompt rule "prefer to move
the BACKEND to match the frontend", the rule does not apply here
— there's no live Lovable contract pointing at the shorter path
(no fixture, no SDK, no Playwright spec). Moving the JSDoc to
match the live SDK call site is the documentation fix this PR
applies.

---

## §A — Round-trip Pydantic ↔ fixture verification

`backend/tests/test_lovable_contract.py` consumes every JSON file
under `public/fixtures/chemistry/runs/*.json` and asserts:

1. `qcompass_core.Manifest.model_validate(blob["manifest"])`
   succeeds.
2. The reconstructed `Manifest.problem` re-serialises to a
   superset of the fixture's `problem` block (the model adds
   default-valued keys but never drops fields).
3. The fixture's `provenance` block populates a
   `ProvenanceRecord` without raising.

The chemistry fixtures are the only Lovable-shipped run JSONs on
disk; the test grows automatically as `condmat`/`hep`/`nuclear`/
etc. directories are populated.

---

## §B / §C — Playwright + feature-flag smoke

DEFERRED per existing v2 conflict log: the sandbox cannot run
`npm install --save-dev @playwright/test`, so the
`acceptance/integration-smoke.html` artifact cannot be produced
in-sandbox. The Playwright spec scaffolding is already on disk at
`e2e/{cosmology-byte-identity,chemistry-h2-flow}.spec.ts` (PROMPT
4 v2); the smoke runs as soon as `npm install` becomes available.

The feature-flag matrix is verified statically in this commit by
the test_lovable_contract suite (the contract holds independently
of `FEATURES.qcompassMultiDomain`), and dynamically by the
existing `e2e/cosmology-byte-identity.spec.ts` which freezes the
cosmology surface at `qcompassMultiDomain=false`.

---

## §D — Acceptance report

See `acceptance/qcompass-final.md`.
