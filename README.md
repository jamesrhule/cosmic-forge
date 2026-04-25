# UCGLE-F1 Workbench (`cosmic-forge`)

Typed, fixture-backed UI for a gravitational-leptogenesis simulator
together with its Python physics + agent backend. This repository is
also the home of the **QCompass** multi-package research workspace
(see §0 below); UCGLE-F1 is the reference implementation, semver-pinned
at `1.0.0` (tag `ucglef1-v1.0.0`).

- `src/`        — the TanStack React frontend (fixture-backed until
                  `FEATURES.liveBackend` is flipped).
- `backend/`    — Python package `ucgle_f1` (M1–M8). See
                  [`backend/README.md`](backend/README.md). The agent
                  orchestrator is served by `ucgle-f1-agent` and exposes
                  the `/mcp/tools/*`, `/v1/chat`, and `/api/*` surface
                  that the frontend consumes.
- `packages/`   — sibling QCompass packages (`qcompass-core`,
                  `qfull-*`). Members are managed by uv workspace.
- `packages/ts/` — TypeScript SDKs managed by pnpm workspace.

## 0. QCompass workspace

This repo is a multi-package monorepo wrapping a stable UCGLE-F1
reference implementation. The workspace layout is:

```
/                         — uv workspace root + pnpm workspace root
├── pyproject.toml        — [tool.uv.workspace] members
├── pnpm-workspace.yaml   — packages/ts/* + apps/*
├── Taskfile.yml          — install / test / serve / verify-freeze / ci
├── .pre-commit-config.yaml
├── backend/              — UCGLE-F1 reference (FROZEN at v1.0.0)
├── packages/
│   ├── qcompass-core/    — protocols, registry, manifest envelope
│   ├── qcompass-router/  — algorithm router
│   ├── qcompass-bench/   — leaderboard harness
│   ├── qfull-chemistry/  — quantum chemistry
│   ├── qfull-condmat/    — condensed matter
│   ├── qfull-hep/        — high-energy phenomenology
│   ├── qfull-nuclear/    — ab-initio nuclear
│   ├── qfull-amo/        — atomic, molecular, optical
│   ├── qfull-gravity/    — gravitational waves + leptogenesis
│   ├── qfull-statmech/   — statistical mechanics
│   └── ts/qcompass-frontend-sdk/ — typed TS client
└── apps/                 — reserved for new pnpm-managed UIs
```

### Freeze contract

`backend/src/ucgle_f1/`, `backend/audit/`, `src/`, `public/fixtures/`,
`supabase/`, `.lovable/`, and `wrangler.jsonc` are held byte-stable
under tag `ucglef1-v1.0.0`. Drift is detected by
`.github/workflows/ucglef1-drift-alarm.yml`, which compares
`dirhash backend/audit` against `backend/audit/golden.lock` on every
PR. Mutating `golden.lock` requires the **`physics-reviewed`** PR
label.

`task verify-freeze` prints `freeze intact` when the audit hash matches.

### Common workflows

```bash
task install          # uv sync + pnpm install + corepack pin
task verify-freeze    # check the UCGLE-F1 freeze contract
task test-ucglef1     # backend unit suite (no slow tests)
task audit-ucglef1    # S1–S15 + A1–A6 audit
task ci               # everything above + lint + test-frontend
```

### Where new code lives

New simulation domains land in `packages/qfull-*`. Cross-domain
plumbing (provenance envelopes, manifest schemas, backend routing,
classical reference adapters) lives in `packages/qcompass-core` and
must NOT import from `ucgle_f1` or any `qfull-*` sibling — coupling
flows through `qcompass-core` protocols only.

## 1. Running the shell

```bash
npm install
npm run dev
```

No environment variables are required. `VITE_API_URL` is read in
`src/config/features.ts` but ignored while `FEATURES.liveBackend === false`.

## 2. Handoff to Claude Code

The frontend treats the service layer as the single integration point.
Each function below has a JSDoc comment in code that names the intended
backend endpoint. Below is a checklist mirror.

### 2.1 Service functions → backend endpoints

| Function | File | Intended backend |
|---|---|---|
| `getBenchmarks()` | `src/services/simulator.ts` | `GET /api/benchmarks` |
| `getRun(id)` | `src/services/simulator.ts` | `GET /api/runs/{id}` |
| `listRuns()` | `src/services/simulator.ts` | `GET /api/runs` |
| `startRun(config)` | `src/services/simulator.ts` | `POST /api/runs` (body: `RunConfig` → `{ runId }`) |
| `streamRun(runId)` | `src/services/simulator.ts` | `SSE GET /api/runs/{runId}/stream` (or `WS /ws/runs/{runId}`) |
| `getAuditReport(runId)` | `src/services/simulator.ts` | `GET /api/runs/{runId}/audit` |
| `getScan(scanId)` | `src/services/simulator.ts` | `GET /api/scans/{scanId}` |
| `sendMessage(...)` | `src/services/assistant.ts` | `WS /ws/assistant` (or SSE `POST /api/assistant/messages`) |
| `listModels()` | `src/services/assistant.ts` | `GET /api/models` |
| `installModel(modelId)` | `src/services/assistant.ts` | `SSE POST /api/models/{modelId}/install` |
| `uninstallModel(modelId)` | `src/services/assistant.ts` | `DELETE /api/models/{modelId}` |
| `getModelStatus(modelId)` | `src/services/assistant.ts` | `GET /api/models/{modelId}/status` |
| `listArtifacts(runId)` | `src/services/artifacts.ts` | `GET /api/runs/{runId}/artifacts` |
| `downloadArtifact(ref)` | `src/services/artifacts.ts` | `GET /api/runs/{runId}/artifacts/{name}` |

All functions throw `ServiceError` with a typed `.code`
(`NOT_FOUND` · `INVALID_INPUT` · `UPSTREAM_FAILURE` · `STREAM_ABORTED` ·
`NOT_IMPLEMENTED`).

### 2.2 Feature flags (`src/config/features.ts`)

| Flag | Purpose |
|---|---|
| `FEATURES.liveBackend` | Switch fetch from `/public/fixtures` to `API_BASE_URL`. |
| `FEATURES.liveAssistantToolDispatch` | Wire assistant tool-call `Apply` buttons to real app actions. |
| `FEATURES.liveModelManagement` | Enable real local-model install / uninstall. |

### 2.3 Assistant tool names (`ToolName`)

`load_run · compare_runs · start_run · open_benchmark · summarize_audit ·
suggest_parameters · export_report · cite_paper · plot_overlay`

Each has a fixture transcript at
`public/fixtures/chat/transcripts/<tool>.jsonl`. The UI renders
`<ToolCallCard>` with collapsible arguments, collapsible result, and an
`Apply` button — wire the button to dispatch the named tool.

### 2.4 Fixture files

```
public/fixtures/
├─ benchmarks.json                    BenchmarkIndex
├─ models.json                        ModelDescriptor[]
├─ runs/
│  ├─ kawai-kim-natural.json          RunResult (V2 baseline)
│  ├─ starobinsky-standard.json       RunResult
│  ├─ gb-off-control.json             RunResult (decoupling check)
│  └─ failing-run.json                RunResult (status: failed)
├─ scans/xi-theta-64x64.json          ScanResult
├─ formulas/F1-F7.json                Equation-gallery data
├─ events/
│  ├─ run-kawai-kim.jsonl             RunEvent stream
│  └─ install-llama-8b.jsonl          InstallEvent stream
├─ chat/transcripts/<tool>.jsonl      AssistantEvent streams (one per ToolName)
└─ artifacts/                         Sample download blobs
```

To replace fixtures with real data: swap files in place — schemas in
`src/types/domain.ts` are the contract.

### 2.5 Stub validators to replace with physics

| File | Replace with |
|---|---|
| `src/lib/validity.ts` | Real CMB / reheating / unitarity checks for `RunConfig`. |
| `src/lib/potentialValidator.ts` | AST whitelist + differentiability check for the custom Python potential. |

## 3. Implementation status

This first pass delivers the foundation — types, services, fixtures,
design system, and shared display components. The full three-view layout
(Configurator, Control, Research) and chat drawer are scaffolded as the
homepage demo and remain to be split into dedicated routes in
`src/routes/`. All seams the backend needs are already in place.

## 4. Stack

TanStack Start (Vite + React 18 + TS strict, file-based routes under
`src/routes/`) · Tailwind v4 + shadcn/ui · TanStack Query · Zustand ·
react-hook-form + zod · KaTeX · Recharts · CodeMirror 6
(`@uiw/react-codemirror` + `@codemirror/lang-python`) · lucide-react ·
react-markdown + remark-gfm + rehype-katex.
