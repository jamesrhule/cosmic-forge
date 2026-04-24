# Visualizer fixtures — seven JSON timelines + one JSONL stream

Goal: produce the eight files registered in `src/services/visualizer.ts` so the Visualizer can boot end-to-end against fixtures, with each timeline numerically consistent with the run and formula it claims to visualize.

## Files to create

Under `public/fixtures/visualizations/`:

1. `kawai-kim-natural.json` — F1, run `kawai-kim-natural`, η_B → 6.1e-10
2. `starobinsky-standard.json` — F1, run `starobinsky-standard`, η_B → 5.78e-10
3. `gb-off-control.json` — F2, run `gb-off-control`, η_B → 1.02e-14 (chirality should collapse to ~0)
4. `f2-nieh-yan-demo.json` — F2 demo, anchored on Kawai-Kim baseline, η_B target ≈ 4.8e-10
5. `f3-large-N-demo.json` — F3, KK-tower variant, anchored on Starobinsky baseline, η_B target ≈ 3.4e-10
6. `f5-resonance-demo.json` — F5, modulated reheating, anchored on Kawai-Kim, η_B target ≈ 2.1e-10
7. `f7-stacked-demo.json` — F7, resonant Higgs portal, anchored on Starobinsky, η_B target ≈ 1.6e-10

Under `public/fixtures/visualizations/streams/`:

8. `kawai-kim-live.jsonl` — one `VisualizationFrame` per line, 60 frames, used by `streamVisualization`.

## Generation strategy

A single Python script (`scripts/gen_visualizer_fixtures.py`, run once via `code--exec`, not shipped to the bundle) emits all eight files. Determinism: seeded NumPy RNG keyed off the timeline `runId` so fixtures regenerate byte-identically.

Per timeline:
- 240 frames covering τ ∈ [-60, 5] (e-folds), partitioned into phases:
  `inflation` 0–139, `gb_window` 140–179, `reheating` 180–209, `radiation` 210–229, `sphaleron` 230–239.
- 24 k-modes per frame on a log grid k ∈ [1e-4, 1e2] in horizon units; F3/F5 add a `kk_level ∈ {0..4}` field.
- For each mode: `h_plus_re/im`, `h_minus_re/im` evolved as a damped oscillator with phase-dependent amplification inside the GB window. `alpha_sq_minus_beta_sq` ramps 0 → A_max during the window (A_max chosen per variant). `in_tachyonic_window` set when frame ∈ gb_window AND k within a variant-specific band.
- `B_plus`, `B_minus`: chiral-asymmetric Gaussian bump centered on frame 160; |B_+ − B_−| scaled by run's `xi`. For `gb-off-control` (ξ=0) both bumps are zero.
- `xi_dot_H`: smoothed step matching `B_plus + B_minus`.
- `lepton_flow.eta_B_running`: monotone interpolation from 0 at frame 0 to **the run's exact `eta_B.value`** at the final frame (or the F-variant's target for the demo runs that don't have a backing run). Intermediate flow magnitudes (`chiral_gw`, `anomaly`, `delta_N_L`) chosen so that `delta_N_L ≈ chiral_gw × theta_grav − washout_term` and the final ratio reproduces the variant's clean-orders profile.
- `sgwb_snapshot` attached at three frames (source / post-reheat / today). The "today" snapshot is **resampled from the run's existing `spectra.sgwb`** (50 of the 280 frequencies, log-uniform), preserving Ω_gw values exactly so that what the Visualizer's spectrum panel shows agrees with what `SGWBPlot` shows in the Research view. Source/post-reheat snapshots scale Ω_gw by physically motivated transfer factors (×1e6 at source, ×30 post-reheat).
- `anomaly_integrand` attached every 10 frames; `running_integral[-1]` matches `eta_B_running` at that frame to within 5% so the panel's cumulative-integral guideline is meaningful.
- `active_terms`: per-phase mapping into the `\htmlId` targets listed in `meta.visualizationHints.formulaTermIds`.

Per-variant differences (only the deltas; everything else inherits from the F1 template):

| Variant | particleColorMode | extraOverlays | A_max | KK levels |
|---|---|---|---|---|
| F1 (kawai-kim, starobinsky) | chirality | [] | 3.5 | none |
| F2 (gb-off, nieh-yan) | chirality | ["torsion_overlay"] | 1.0 / 2.8 | none |
| F3 (large-N) | kk_level | ["kk_tower"] | 2.4 | 0–4 |
| F5 (resonance) | resonance | ["resonance_inset"] | 4.0 | 0–2 |
| F7 (stacked) | condensate | ["wormhole_node"] | 2.0 | none |

`formulaTermIds` for each variant pulled from the `latex` strings in `public/fixtures/formulas/F1-F7.json` (e.g. F1 → `["xi", "theta_grav", "RtildeR", "S_E2", "M1", "fa", "Mstar"]`).

## Consistency invariants (machine-verified after generation)

The generator script ends with assertions and `code--exec` re-runs them as a smoke test:

1. `frames[-1].lepton_flow.eta_B_running` equals the backing run's `eta_B.value` (relative tol 1e-6) for the three runs that have backing fixtures; equals the variant's stated target (rel tol 5%) for the four demo timelines.
2. The final `sgwb_snapshot.Omega_gw` series equals the corresponding subset of the run's `spectra.sgwb.Omega_gw` exactly when a backing run exists.
3. `phaseBoundaries` keys partition `[0, frames.length-1]` with no gap or overlap.
4. Every `active_terms` entry appears in `meta.visualizationHints.formulaTermIds`.
5. `frame.modes.length` constant per timeline → matches `bakeTimelineBuffers`'s expectations.
6. For `gb-off-control`: max(|B_+ − B_−|) < 1e-12 and final `eta_B_running` < 1e-13 (verifies decoupling control still decouples in the visualization).
7. JSONL stream parses line-by-line and every line passes the same per-frame schema validator.

## File-size guardrail

Target ≤ 1.2 MB per JSON timeline (well under the 200 MB ceiling in `services/visualizer.ts`). Numbers serialised with `repr`/`%.6g` to keep payloads small. The JSONL stream stays under 400 KB.

## Out of scope for this turn

- UI panels and `/visualizer` routes (queued for a later turn per the existing plan).
- Live websocket wiring — stream fixture only emulates the contract.
- Backend (Claude Code will mirror the JSON schema; no contract changes here).

## Technical notes

- All writes go to `public/fixtures/visualizations/` and `public/fixtures/visualizations/streams/`. No source under `src/` is touched.
- The generator script lives at `scripts/gen_visualizer_fixtures.py`. It is checked in so the fixtures are reproducible, but it is not imported by the app. Add a one-line entry to README under "Fixtures" pointing at it.
- After generation, run `bun run typecheck` and `bun run build` to confirm the new JSON paths don't trip the Vite asset pipeline (they shouldn't — they're plain `/public` static assets fetched at runtime).

## Acceptance

- All 8 files exist and parse.
- All 7 invariants pass.
- `getVisualization("kawai-kim-natural")` resolves and `bakeTimelineBuffers` produces non-empty `positions[0]` (sanity-checked via a tiny Node script).
- README "Fixtures" section mentions the generator and the consistency contract.
