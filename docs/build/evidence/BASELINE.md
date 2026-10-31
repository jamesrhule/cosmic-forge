# Baseline — measured 31 Oct 2026 (PLAN.md Part 2 step 4)

Commits measured: `origin/main` = `cca2101`, agent branch `claude/ucgle-f1-agent-simulator-agRxR` = `bcc751e`,
router branch `claude/provider-adapters-routing-33xCz` = `37086b7`. Each was checked out into its own git worktree.

Toolchain: Python 3.12.3 (uv 0.11.32 venvs), Node v22.22.0, npm 10.9.4, bun 1.4.4. Playwright 1.64.1 (Chromium only —
`playwright install firefox webkit` is refused by this session's egress proxy).

Freshly resolved Python versions (no lockfile exists, so these float): fastapi 0.162.0, starlette 1.10.0,
sse-starlette 3.6.0, pydantic 2.14.2, numpy 2.5.4, scipy 1.18.1, pytest 9.2.0, pytest-asyncio 1.4.1,
hypothesis 6.170.14.

## Python

Install: `uv venv -p 3.12`; `uv pip install --no-sources -e "backend[dev]" -e packages/<each>` (the plain workspace
install fails on every branch: on the agent branch with "`qcompass-core` is included as a workspace member, but is
missing an entry in `tool.uv.sources`"; on main and the router branch because `qcompass-router` depends on
`qcompass-core`, which does not exist there — those packages were installed with `--no-deps`).

### Backend (`cd backend && pytest -q`)

Unmodified invocation fails at start-up on all three branches:
`PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset` (raised as an error
by `filterwarnings = ["error"]`). With `-o asyncio_default_fixture_loop_scope=function`, collection then fails on every
module that imports `starlette.testclient`: `StarletteDeprecationWarning: Using httpx with starlette.testclient is
deprecated; install httpx2 instead` (starlette 1.10 floated in — a pinning problem, R17). Measured with both
overrides on the command line (measurement only; no code changed):

| Branch | Result |
|---|---|
| main | 2 failed, 64 passed (16 min) |
| agent | 7 failed, 134 passed, 3 skipped, 1 xfailed (19 min) |
| router | 2 failed, 109 passed, 3 skipped (17 min) |

Failures:
- all three: `audit/physics/test_parity_hypothesis.py::test_gb_to_zero_decoupling`
- main, router: `tests/integration/test_domain_parity.py::test_python_mirrors_every_ts_type`
- agent: `tests/test_qcompass_adapter.py::{test_adapter_matches_direct_pipeline_eta_b, test_validate_returns_relative_error,
  test_adapters_import_works_without_qcompass_core, test_freeze_unchanged_after_adapter_runs,
  test_adapter_standard_precision_runs, test_v2_provenance_sidecar_classical_run_fields}` (the six adapter tests shell
  out to bare `python` / depend on the `datetime.utcnow` warning path)

The plan's orientation numbers (agent: 133 passed, 6 failed) differ slightly because this environment installs the
backend and every plugin into one venv.

### Packages (`pytest packages -q --import-mode=importlib`)

| Branch | Result |
|---|---|
| main (`qcompass-router` 6A only) | 25 passed |
| agent (11 packages, backend installed) | 269 passed, 7 skipped |
| router (`qcompass-router` 6A+6B) | 37 passed, 1 skipped |

With the backend installed the agent branch's `test_list_domains_has_eight_real_domains` passes (the plan's
orientation failure appears only when the cosmology plugin is not installed).

## Frontend

| Step | main | agent | router |
|---|---|---|---|
| `npm ci` | fails (ERESOLVE: zod 3 vs zod 4 peer via `@tanstack/zod-adapter`) | fails (same) | fails (same) |
| `npm install --legacy-peer-deps` | ok | ok | ok |
| `vite build` | ok | **fails** — Rollup cannot resolve `react-is` from `recharts` | ok |
| `tsc --noEmit` | 1 error: `src/routes/pricing.tsx(70,20)` `<Link to="/login">` missing required `search` | 0 errors | 3 errors: `SlaterSankey.tsx(70)`, `ShellOccupation.tsx(49)` (recharts formatter types), `visualizerStream.ts(75)` cannot find `@msgpack/msgpack` |
| Vitest | 52 passed; 1 file fails to load (`katex-block.test.tsx`: `@testing-library/dom` missing) | 0 tests; 2 files fail (`e2e/*.spec.ts` picked up by Vitest, `@playwright/test` missing) | 52 passed; 2 files fail (`katex-block.test.tsx`; `manifest.test.ts` vi.mock hoisting error) |
| ESLint | 691 errors, 13 warnings (687 auto-fixable) | 234 errors, 7 warnings | 433 errors, 15 warnings |

### Serving

- `vite preview` cannot serve the build (`dist/server/server.js` missing — the build is a Cloudflare Worker bundle).
- `wrangler dev --config dist/server/wrangler.json` serves it but every SSR request returns 500:
  "Disallowed operation called within global scope" (main baseline defect).
- `vite dev` serves the app; SSR returns HTTP 500 for `/` (benchmarks fixture `fetch failed` during SSR) but the HTML
  renders and hydrates. Screenshots in this campaign are taken from `vite dev` on Chromium at 1440×900.
