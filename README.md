# UCGLE-F1 Workbench — Frontend Shell

Typed, fixture-backed UI for a gravitational-leptogenesis simulator. This
repository is **frontend-only**. Every async operation goes through
`src/services/` and currently returns data from `/public/fixtures/*`.

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

## 4. QA

- Manual chart-resize checklist: [`docs/qa/chart-resizing.md`](docs/qa/chart-resizing.md).
- Enable the per-chart size HUD with `localStorage.setItem("ucgle.devOverlay", "1")` (or append `?devOverlay=1` once); see `src/config/dev-overlay.ts`.

## 4. Stack

TanStack Start (Vite + React 18 + TS strict, file-based routes under
`src/routes/`) · Tailwind v4 + shadcn/ui · TanStack Query · Zustand ·
react-hook-form + zod · KaTeX · Recharts · CodeMirror 6
(`@uiw/react-codemirror` + `@codemirror/lang-python`) · lucide-react ·
react-markdown + remark-gfm + rehype-katex.
