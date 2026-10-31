# P0-02 lane — VIZ-BACKEND (unified `cosmic_forge_viz`)

Branch `build/w0-p002-viz` (base `4b68d9b`). Scope: `backend/src/cosmic_forge_viz/**`,
`backend/tests/viz/**`, this file. `backend/tests/cosmic_forge_viz/**` (agent tests) is
**unmodified**. No change to `backend/audit/**`, `ucgle_f1`, `packages/**`, `src/**`.

## Result

```
cd backend && ../.venv-lane/bin/python -m pytest tests/viz tests/cosmic_forge_viz -q \
  -p no:cacheprovider -o asyncio_default_fixture_loop_scope=function \
  -W 'ignore:Using `httpx` with `starlette.testclient`'
```

- Summary line: `74 passed in 3.65s` — exit code **0**.
- Before this lane (same command at `4b68d9b`): 6 collection errors (every `tests/viz`
  module failed to import against the agent package).
- Versions: Python 3.12.3, pytest 9.2.0, fastapi 0.162.0, starlette 1.10.0,
  pydantic 2.14.2, zarr 3.4.2, ormsgpack installed (msgpack path exercised).
  Env: `uv venv .venv-lane` + `uv pip install --no-sources -e "backend[dev,viz]" pytest pytest-asyncio httpx`.
- The `-W` and `-o` overrides are measurement-only (starlette 1.10 float / pytest-asyncio
  config warning); pinning lands in P0-04.
- Side check (not a gate, frozen file untouched): `audit/agent/test_a7_qcompass_routes.py`
  gives the **same** 5 failures before and after this lane (`KeyError: 'runId'`, 503s from the
  run-creation path, not from viz). `cosmic-forge-viz check` and `bake --domain gravity` work.

## Per-test disposition — `backend/tests/viz` (48 tests)

| Test | Disposition |
|---|---|
| test_baker.py::test_bake_chemistry | kept, unmodified |
| test_baker.py::test_bake_cosmology_marks_variant | kept, unmodified |
| test_downsample.py (6 tests) | kept, unmodified |
| test_fixtures.py::test_synthesize_frames_is_deterministic[×6] | kept, unmodified |
| test_fixtures.py::test_phases_cover_progression[×6] | kept, unmodified |
| test_fixtures.py::test_manifest_includes_progression | kept, unmodified |
| test_fixtures.py::test_synthesize_unknown_domain | kept, unmodified |
| test_protocol.py::test_frame_roundtrip[×6] | kept, unmodified |
| test_protocol.py::test_msgpack_path_when_available | kept, unmodified |
| test_schema.py (9 tests) | kept, unmodified |
| test_server.py — 9 of 10 tests | kept, unmodified |
| test_server.py::test_ws_stream | **ported** (ledger L1) |

Removed: none.

## Ledger

**L1 — `tests/viz/test_server.py::test_ws_stream` ported to the envelope WS protocol.**
Old assertions: first binary message is a msgpack frame (`first[0] != ord("{")`),
`decode_frame(first).domain == "chemistry"`, two more `receive_bytes()`, then
`ws.receive_text() == "__done__"`.
New assertions: a `header` envelope first (`decode(...)["type"] == "header"`,
`payload["n_frames"] == 3`); then the same msgpack check and `decode_frame(first).domain ==
"chemistry"` on the first frame; the two following frames now also assert
`domain == "chemistry"` (strictly stronger); end is `decode(ws.receive_bytes())["type"] == "end"`.
Every behaviour previously asserted (3 frames, msgpack wire, typed decode, explicit end marker) is
still asserted. Reason: one WS protocol (R20) — the envelope protocol is the one the agent tests
and the M8 `/ws/qcompass/...` route already use.

**L2 — agent `CosmologyFrame` flat/`CosmologyModeBlock` fields → router-branch structured shape.**
Same-named fields had different types across branches (e.g. `modes`, `B_plus`, `lepton_flow`).
The router shape is canonical because it matches `src/types/visualizer.ts`; `CosmologyModeBlock`
is replaced by `_ModeSample` list. Agent-only fields kept: `HepFrame.particle_obs`,
`NuclearFrame.model_domain`, `ChemistryFrame.slater` (Sankey matrix), `GravityFrame`,
`StatmechFrame`, `VisualizationTimeline` (+ new `synthetic`, `formula_variant`).

**L3 — phase vocabulary.** Router vocabulary is canonical (`gb_window`, `sphaleron`, …). The
agent's `leptogenesis` epoch maps to `sphaleron` in `formulas_at_phase` (`_PHASE_ALIASES`).
Gravity (`ground→quench→thermalize→measure`) and statmech (`warmup→equilibrium→measure`) added.

**L4 — POST `/visualization/render` with no body.** Agent: synchronous `bake_synthetic`, 200.
Router: 202 `{"status":"queued"}`. Unified: 202 queued **and** the synthetic bake runs as a
background task when a viz root is configured (both behaviours kept). With a provenance body:
agent behaviour, 200 + bake info.

**L5 — server viz root / GET source.** Agent server baked synthetic JSON into
`~/.qcompass/viz` on every miss and set `VIZ_ARTIFACTS` process-wide in `create_app`. Unified:
root = `create_app(viz_root=)` → `$VIZ_ARTIFACTS` → none; baked snapshot served when present,
otherwise `total` synthetic frames (flagged `synthetic: true`, R7) without writing to disk; no
global env mutation. `bake_synthetic` / CLI `bake` still default to `~/.qcompass/viz`.

**L6 — GET `max_frames` default.** Agent default 256, router default none. Router semantics kept
(frontend contract); the M8 `/api/qcompass/.../visualization` route keeps its own 256 default.
SSE keeps the agent's `adaptive_decimate` cap (≈128 frames) unless `max_frames` is given.

**L7 — Zarr writer.** Agent `_write_zarr` used the zarr‑2 API (`zarr.open`/`create_dataset`) and
silently produced nothing on zarr 3. Replaced by router `bake_timeline` (zarr v3), now also called
by `bake_synthetic` (`zarr_path` populated; still soft-fails to `None`).

**L8 — seeds.** Router used `hash(run_id)` (salted per process → nondeterministic across
processes). Replaced by `fixtures.stable_seed` (crc32).

**L9 — CLI.** Router Typer CLI (`serve`, `bake` zarr-only, `demo`) merged into the agent argparse
CLI: `bake` (JSON + Zarr, `--formula-variant`), `demo`, `serve`, `check` (now 8 domains).

## Capability diff — router-branch capability → where it lives now

| RB capability | Location |
|---|---|
| Structured per-domain frames (`_ModeSample`, orbitals, lattice, plaquettes, shells, atoms) | `schema.py` |
| `VisualizationManifest`, `frame_for_domain`, `Domain`, `VisualizationFrame` union | `schema.py` (`frame_class_for_domain` alias kept) |
| `phase_for`, `progression` | `phases.py` (agent `phase_for_tau`, `phases_for_domain` alongside) |
| `active_terms_for_variant`, `default_active_terms`, `all_known_terms`, `assert_terms_known` | `formulas.py` |
| `downsample_indices`, `downsample_frames`, `fps_to_target` | `downsample.py` (agent decimators are thin wrappers) |
| `encode_frame`, `decode_frame`, `has_msgpack` | `protocol.py` (frame envelope; bare dicts still decode) |
| `synthesize_frames`, `synthesize_manifest`, per-domain generators | `fixtures.py` (+ gravity, statmech; agent `build_synthetic_timeline` built on top) |
| `bake_timeline`, `read_manifest`, `read_payloads` (zarr v3) | `baker.py` |
| `/manifest` endpoint, `total`/`max_frames`/`fps` params, CORS, `ucgle-fN-` variant inference, WS 1008 on unknown domain | `server.py` |
| `demo` CLI command | `cli.py` |

## Protocol notes for the frontend lane

Base: viz server (`cosmic-forge-viz serve`, default `127.0.0.1:8765`). Domains:
`cosmology chemistry condmat hep nuclear amo`; gravity/statmech are only on the M8 routes
`/api/qcompass/domains/{domain}/runs/{id}/visualization` and
`/ws/qcompass/domains/{domain}/runs/{id}/visualization` (same envelope protocol).

- `GET /api/runs/{domain}/{id}/manifest?total=` → `VisualizationManifest`
  `{run_id, domain, frame_count, formula_variant, bake_uri, metadata:{phases, seed?, synthetic?}}`.
- `GET /api/runs/{domain}/{id}/visualization?total=&max_frames=` → `{run_id, domain,
  schema_version, synthetic, n_frames, manifest, frames}`. `manifest.ts` reading
  `{manifest, frames}` keeps working; new: `synthetic` must be surfaced in the UI (R7).
- `POST /api/runs/{domain}/{id}/visualization/render` → 202 `{run_id, domain, status:"queued"}`
  (no body) or 200 bake info (provenance body).
- **SSE** `GET /sse/runs/{domain}/{id}/visualization?total=&fps=&max_frames=`: named events
  `header` (data = `{run_id, domain, n_frames, synthetic, manifest}`), `frame` (data = bare frame
  JSON, one line), `done` (data `{}`). Change for `visualizerStream.ts`: ignore/consume `header`.
- **WS** `/ws/runs/{domain}/{id}/visualization?total=&fps=`: **every** message is a binary
  envelope `{type, seq, tau, payload}` (msgpack; JSON bytes if server lacks ormsgpack —
  first byte `{`). Sequence: `header` (seq 0, payload as SSE header) → `frame` (seq 1..N,
  payload = frame dict) → `end`. **Breaking for `visualizerStream.ts`:** frames are no longer
  bare msgpack frames and the text `"__done__"` sentinel is gone — unwrap `payload` when
  `type == "frame"`, stop on `type == "end"`, handle `type == "error"`. Server holds the socket
  open after `end` until the client closes. Unknown domain → close 1008 before accept.
- Frame shapes: the router-branch structured shapes (unchanged for the frontend). Additive:
  `HepFrame.particle_obs`, `NuclearFrame.model_domain`, `ChemistryFrame.slater`,
  `GravityFrame`, `StatmechFrame`.
- **For P4-04:** `active_terms` uses the backend term IDs (`kinetic`, `GB_window`, `anomaly`, …
  plus F-ids when couplings are given); main's frontend fixtures use equation-symbol IDs
  (`xi`, `theta_grav`, `RtildeR`) — a third namespace that needs a mapping table.
