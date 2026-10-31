# R19 control run (PLAN.md correction 7a)

## What was compared
- **Control (main):** branch `build/r19-control` = `origin/main` `cca2101` + only the Workers SSR-fix code from `e440756` (chat id, ASSETS fixture loader), `a0ae4ea` (rebake GPU buffers) and `24c295d` (serialisable domain loaders, `sideEffects`).
  - All code hunks applied cleanly; nothing was hand-applied. The only conflict was `docs/build/LEDGER.md` plus the evidence PNGs in `a0ae4ea`, all docs, so dropped.
  - The harness was added unchanged from the W0 branch: `playwright.config.ts`, `e2e/cosmology-byte-identity.spec.ts`, `e2e/stable.ts`, `e2e/urls.ts`, and `scripts/e2e_serve.sh` (`bun run build` → `npm run build`).
  - The render workflow uses `npm install --legacy-peer-deps`, main's documented working install (BASELINE.md); main's bun lockfile points at a private mirror. That install also refreshed main's out-of-sync `package-lock.json`, the same resolution CI performs.
  - CI rendered the three routes on chromium, firefox and webkit with `--update-snapshots` and committed them as `a379fc2`, a run of the workflow in the control commit `3e2b1fa`.
- **W0:** `build/w0-consolidate` baselines (`e2e/__screenshots__/*/cosmology-byte-identity.spec.ts/*.png`, pinned in `R19.sha256`).
- **Comparator:** Playwright's own image comparator (`playwright-core/lib/server/utils/comparators.js`, the one `toHaveScreenshot`/`toMatchSnapshot` use) with the default per-pixel threshold.
  - Pass/fail at `maxDiffPixelRatio: 0.001`: `expect(controlPng).toMatchSnapshot([...], { maxDiffPixelRatio: 0.001 })` against the W0 PNG.
  - Exact counts: the same comparator at `maxDiffPixels: 0`. The ratio is the differing pixels divided by the image area.

## Results (per route, per browser)

| Browser | Route | W0 size | Control size | Differing px | Ratio | At 0.001 |
|---|---|---|---|---|---|---|
| chromium | `/` | 1440×2478 | 1440×2478 | 8 | 2.24e-6 | pass |
| chromium | `/visualizer` | 1440×900 | 1440×900 | 0 | 0 (byte-identical PNG) | pass |
| chromium | `/visualizer/kawai-kim-natural` | 1440×900 | 1440×900 | 0 | 0 | pass |
| firefox | `/` | 1440×2478 | 1440×2478 | 1386 | 3.88e-4 | pass |
| firefox | `/visualizer` | 1440×900 | 1440×900 | 0 | 0 | pass |
| firefox | `/visualizer/kawai-kim-natural` | 1440×900 | 1440×900 | 266 | 2.05e-4 | pass |
| webkit | `/` | 1440×**2477** | 1440×**2478** | 1826 | 5.12e-4 | **fail (size mismatch)** |
| webkit | `/visualizer` | 1440×900 | 1440×900 | 267 | 2.06e-4 | pass |
| webkit | `/visualizer/kawai-kim-natural` | 1440×900 | 1440×900 | 653 | 5.04e-4 | pass |

Every pixel ratio is below 0.001. One route fails the comparator: webkit `/`. Playwright fails any size mismatch whatever the ratio.

## webkit `/`: each visible difference, and why it is not a cosmology capability or physics change
I inspected the control PNG and the comparator's diff image.
1. **Page height 2477 vs 2478 px (one row).** The full-page capture height differs by one CSS pixel, so the masked build-stamp footer band sits one row lower. Sub-pixel layout height rounds differently between the two builds' WebKit page boxes. No element is added, removed or resized: the content above the footer lines up row for row in the diff.
2. **Glyph-edge anti-aliasing** on the header ("UCGLE-F1 Workbench", "Configurator", "Sign in"), the KaTeX η_B formula and the "Active context" chips. Only isolated edge pixels of glyphs differ. The text, the formula and every displayed value (8.50×10⁻³, 7.80×10⁻¹, 4.60×10⁻², 1.00×10¹⁰, 1.00×10¹⁶, (2.40×10¹⁸)², "4 benchmarks available", "~23 CPU·min", "Admissible") are identical.
Neither difference touches what cosmology renders or computes. These are rasterisation and rounding artefacts of the same DOM.

## The other non-zero routes
I inspected each diff image: firefox `/`, firefox and webkit kawai-kim, webkit `/visualizer`, chromium `/`. The differing pixels are glyph-edge anti-aliasing on labels, panel titles, axis ticks and KaTeX, plus (firefox `/`) a 1px vertical offset of the KaTeX box's bottom rule. Every data mark is pixel-identical: phase-space points, the Γ curves, the Ω_GW spectrum, the integrand bars and the running ∫. The same three routes show the same content in both builds.

## Conclusion
With main given only the Workers SSR fixes, cosmology on main and on `build/w0-consolidate` renders the same content on all three browsers. Eight of nine pairs pass Playwright at `maxDiffPixelRatio: 0.001`. The ninth (webkit `/`) differs by one row of page height plus anti-aliasing, at a 5.12e-4 pixel ratio, with no change to any cosmology capability or physics. No fix is required.

**Watch item:** if WebKit's full-page height is not stable across runs, the locked webkit `/` baseline (2477 px) could flake. The CI playwright job on the W0 PR will show this. If it flakes, any re-baseline is `BLOCKED-ON-JAMES:r19-rebaseline` (R19.sha256 is James-only).

`build/r19-control` was deleted after this file was written.
