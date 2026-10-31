# `@qcompass/frontend-sdk`

Typed TypeScript SDK that wraps the qcompass HTTP / WS surface
(PROMPT 8 v2 §C). Used by the React shell at `/src` and any future
app under `/apps`.

## Surface

```ts
import { QcompassClient, chemistryService, hepService } from "@qcompass/frontend-sdk";

const client = new QcompassClient({ baseUrl: import.meta.env.VITE_API_URL });
const chem   = chemistryService(client);

const sub    = await chem.submit(manifest);          // POST /api/qcompass/domains/chemistry/runs
const run    = await chem.get(sub.runId);            // GET .../runs/{run_id}
for await (const ev of chem.stream(sub.runId)) {     // SSE .../runs/{run_id}/stream
  // ev.event in {history, status, end}; ev.data is the payload.
}
const viz    = await chem.visualization(sub.runId);  // GET .../runs/{run_id}/visualization
const ws     = chem.openWs(sub.runId);               // WS  /ws/qcompass/...
```

Top-level helpers:

- `listDomains`, `getDomainSchema`
- `submitRun`, `getRun`, `streamRun`
- `getVisualization`, `openVisualizationStream`
- `listScans`, `getScan`, `createScan`, `deleteScan`

Per-domain wrappers: `chemistryService`, `cosmologyService`,
`hepService`, `nuclearService`. Adding a new domain wrapper is
~12 LoC at the bottom of `src/services.ts`.

## Live vs fixture

The SDK never reads `FEATURES.liveBackend`. The React layer
chooses between a live `QcompassClient` and the existing fixture
loader (`src/services/qcompass/*.ts`) based on the flag. When the
flag is `true`, services hit the FastAPI surface; when `false`,
they keep returning fixtures. This preserves the byte-stable
cosmology contract.

## Type generation

`src/types.ts` is **hand-aligned** today; PROMPT 8 v2 §C names
`datamodel-code-generator >= 0.26` as the canonical generator.
Once the generator runs in CI, regenerate via:

```bash
pnpm --filter @qcompass/frontend-sdk run regen-types
```

The current generator script:

```
datamodel-codegen \
  --input ../../qcompass-core/src/qcompass_core \
  --input-file-type pydantic \
  --output ./src/types.ts \
  --target-python-version 3.12
```

Hand edits stay limited to additions outside the auto-generated
section so a regen diff is mechanical.

## Boundary

The SDK is dependency-free at runtime: native `fetch`,
`EventSource`, and `WebSocket`. It targets Node >= 18 and modern
browsers. ormsgpack-framed binary frames require an external
decoder (we ship the JSON fallback only).

The legacy frontend at the repo root (`/src`, served by Vite +
TanStack Start) is **not** part of the pnpm workspace; it imports
this package via the workspace symlink set up at the root
`tsconfig.json` paths block.
