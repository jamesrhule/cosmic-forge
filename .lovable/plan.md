## Review outcome

Verified that all original UCGLE-F1 features are intact and that the new QCompass scaffolding (domain registry, cosmology adapter, qcompass stubs, profiles, password reset, storage-first visualizer) compiles and builds cleanly:

- `bunx tsc --noEmit` → clean
- `bun run build` → clean (production SSR + client bundles)
- Configurator (`/`), Visualizer (`/visualizer`, `/visualizer/$runId`), auth routes, UserMenu, persistence helpers — all unchanged in behavior.
- One-way isolation contract holds: `src/services/*` does not import `src/lib/domains/*` or `src/lib/qcompass/*`.

The runtime warnings shown in the preview ("Importing a module script failed", "error during concurrent rendering but React was able to recover") correlate with the `[vite] server connection lost. Polling for restart...` log — these are stale dynamic-chunk imports during HMR, not bugs. React recovered automatically and they clear on a hard reload.

## Single follow-up change

The only reason the new domain selector chip is not visible in the preview is that `FEATURES.domainsRegistry` defaults to `false`. Per your choice, flip it to default-on everywhere.

### Edit

`src/config/features.ts`

```ts
domainsRegistry:
  (typeof import.meta !== "undefined" &&
    import.meta.env?.VITE_DOMAINS_REGISTRY === "false")
    ? false
    : true,
```

Effect:
- Chip renders in the header on `/` (Configurator) for all builds.
- Cosmology · UCGLE-F1 is the only enabled entry; the seven Phase 2 domains render as locked rows with their tooltip reasons.
- The cosmology service path is unaffected — the adapter wraps `services/simulator.ts` with byte-identical behavior.
- Escape hatch preserved: setting `VITE_DOMAINS_REGISTRY=false` in env will hide the chip again if needed.

### Verification after the edit

1. `bunx tsc --noEmit` (expect clean)
2. `bun run build` (expect clean)
3. Visual: open `/`, confirm a "Compass · Cosmology · UCGLE-F1" chip appears in the header next to the dev-build pill; opening it lists 1 enabled + 7 disabled rows.
4. Confirm `/visualizer` still renders the run grid and the configurator form still submits.

No other files change. No migrations. No new dependencies.
