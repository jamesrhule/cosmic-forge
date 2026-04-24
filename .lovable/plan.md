# Plan: Builder Quickstart One-Pager

Create a single self-contained Markdown file that an external contributor can follow in under 5 minutes to (a) run the frontend locally against bundled JSON fixtures (no backend, no Supabase) and (b) verify that every route renders correctly.

## Deliverable

One file: `/mnt/documents/QUICKSTART_BUILDERS.md`

Delivered to the user via a `<lov-artifact>` tag (mime `text/markdown`).

## Content outline (one page, ~1 screen of scrollable text)

1. **Prereqs** — Node 20+, `bun` or `npm`, no env vars required.
2. **Run** — `bun install && bun run dev`, open `http://localhost:8080`.
3. **Fixtures-first explainer** — fixtures live in `public/fixtures/` and are loaded by `src/lib/fixtures.ts` via `loadFixture()` / `loadJsonlFixture()`. While `FEATURES.liveBackend === false` (default in `src/config/features.ts`), every service call in `src/services/*` resolves from these JSON/JSONL files. No backend needed.
4. **Fixture map** — short table: `benchmarks.json`, `models.json`, `runs/*.json`, `scans/*.json`, `chat/transcripts/*.jsonl`, `events/*.jsonl`, `artifacts/<slug>/*`.
5. **Route verification matrix** — every route in `src/routes/` with: path, what to expect, fixture(s) it pulls, and a 1-line "pass" criterion. Also note the **≥1024px viewport requirement** for `/` (Configurator) so reviewers don't mistake the responsive fallback for a bug.
   - `/` → Configurator (needs ≥1024px wide)
   - `/visualizer` → run picker (lists fixture runs)
   - `/visualizer/$runId` → six-panel visualizer (try `kawai-kim-natural`, `starobinsky-standard`, `gb-off-control`, `failing-run`)
   - `/qa` → QA checklist harness
   - `/login`, `/reset-password`, `/auth/callback` → auth pages (render without a session)
6. **Smoke check (optional)** — one-liner curl loop that hits each route and asserts HTTP 200 from the SSR server.
7. **Common gotchas** — narrow viewport fallback, `timeline_sign_failed` log line is benign when Supabase storage is empty, never edit `routeTree.gen.ts` / `src/integrations/supabase/*`.
8. **Where to make changes next** — `src/services/*` is the seam to swap fixtures for a real backend (flip `FEATURES.liveBackend`).

## Process

1. Write `/mnt/documents/QUICKSTART_BUILDERS.md` with the content above. Keep it terse — fits on one printed page (~80 lines, ~5 KB).
2. Verify with `wc -l` and `head` that the file is readable and on-page-length.
3. Emit `<lov-artifact path="QUICKSTART_BUILDERS.md" mime_type="text/markdown"></lov-artifact>`.

## Out of scope

- Backend (Python `ucgle_f1`) setup — the doc explicitly states fixtures are sufficient and points to `backend/README.md` for the live path.
- Deployment / Cloudflare Worker specifics.
- Detailed API contract (already covered by `PROJECT_OVERVIEW.md` from the prior turn — this doc cross-references it).
