# Visualizer wire contract

The frontend assumes the simulator emits timelines that satisfy a small set
of invariants beyond the static type / Zod shape. These are enforced in
**development builds** by `assertVisualizationInvariants` (see
`src/lib/visualizerSchema.ts`); production builds tree-shake the call.

## Per-frame array-length invariants

For every `VisualizationFrame`:

- `sgwb_snapshot` (when present) — `f_Hz.length === Omega_gw.length === chirality.length`.
  A mismatch silently corrupts the SGWB chart legend ↔ data alignment.
- `anomaly_integrand` (when present) — `k.length === integrand.length === running_integral.length`.

Violations throw `VisualizationContractError("Frame N <field>: …")` pointing at
the offending frame index.

## `active_terms` shape

Send the **bare** term id (e.g. `"xi"`, `"M1"`, `"theta_grav"`), not the
prefixed DOM id (`"vfx-xi"`). The formula panel strips the `vfx-` prefix
from rendered KaTeX nodes before comparing against `active_terms`; a
prefixed value would never glow.

## Buffer cap

`BakedTimelineBuffers.maxModes` is bounded by `MAX_INSTANCES = 4096`
(`src/lib/visualizerBake.ts`). The R3F `InstancedMesh` in
`panel-phase-space.tsx` consumes `baked.maxModes` directly as its instance
count, so any timeline with more than `MAX_INSTANCES` simultaneous modes
will throw at bake time rather than crash the GPU draw call later.
Tune the cap on **both** sides in lockstep if more particles are needed.

## Formula variants

`FORMULA_VARIANTS` in `src/types/visualizer.ts` is the single source of
truth for the F1–F7 enum. Fixture schemas, run-pickers, and any new
iteration over variants should import from there rather than hand-listing
the strings.
