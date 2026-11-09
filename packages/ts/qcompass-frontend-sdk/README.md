# `@qcompass/frontend-sdk`

Typed TypeScript client for the QCompass compute API
(`ucgle_f1.m8_agent.server.build_app`). Used by the workbench at `/src`
(through `src/lib/sdk.ts`) and any future app under `/apps`.

## Types are generated (P4-02)

FastAPI's OpenAPI document is the contract (PLAN Part 4). Two files are
generated from it and committed:

- `openapi.json`: `build_app().openapi()` with sorted keys
  (`scripts/dump_openapi.py`);
- `src/generated/openapi.ts`: `openapi-typescript` 7.13.0 (pinned in the root
  `package.json`, MIT) over that document.

Regenerate after changing a backend route or response model:

```bash
bun run sdk:gen          # or scripts/gen_sdk_types.sh
bun run sdk:check        # what CI runs (backend job): fails when stale
```

Never edit the generated files. `src/api.ts` reads them
(`JsonResponse<"/api/benchmarks", "get">`, `Schemas["DomainRunResult"]`);
`src/types.ts` re-exports the schemas under stable names and holds the few
hand-written types the OpenAPI document does not describe (free-form request
bodies, SSE event payloads, visualization frames), each with the reason.

## Surface

```ts
import { QcompassClient, submitRun, streamRun, getRun } from "@qcompass/frontend-sdk";

const client = new QcompassClient({
  baseUrl: import.meta.env.VITE_API_URL,
  headers: async () => ({ Authorization: `Bearer ${await token()}` }),
});

const sub = await submitRun(client, "chemistry", { molecule: "H2" }); // 202 queued
for await (const ev of streamRun(client, "chemistry", sub.runId)) {
  // ev.event: history | status | progress | log | end; ev.data: the payload
}
const run = await getRun(client, "chemistry", sub.runId); // DomainRunResult
```

One function per route in `src/services.ts` (ops, UCGLE-F1 runs, chat and
models, domains, runs, visualization, scans, tenants, verdict, literature),
plus per-domain namespaces (`chemistryService(client)` …). Errors raise
`QcompassError` with the HTTP status and the parsed error envelope; the app
maps them to its `ServiceError`.

SSE uses `fetch` streaming (`parseSse`), so auth headers are sent and named
events (`event: status`) are delivered, which `EventSource` cannot do.

## Live vs fixture

The SDK never reads feature flags. The app decides: with `VITE_API_URL` set
(`DATA_SOURCE === "api"` in `src/config/features.ts`) every service calls the
SDK and reads no fixtures; without it, services read bundled fixtures.

## Boundary

Dependency-free at runtime: native `fetch`, `ReadableStream` and
`WebSocket` (Node >= 18, modern browsers). ormsgpack-framed binary frames
need an external decoder (the SDK ships the JSON fallback, `decodeFrame`).
The package is a bun workspace member and is also reachable through the
`@qcompass/frontend-sdk` path alias in the root `tsconfig.json`.
