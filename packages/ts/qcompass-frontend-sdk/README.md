# `@qcompass/frontend-sdk`

Typed TypeScript SDK that mirrors the `qcompass-core` Python protocols
for use in React shells under `apps/*`.

## Status

**Placeholder.** Created during Phase 0 (commit `ucglef1-v1.0.0`)
as a reserved namespace. The real SDK is generated from
`qcompass-core` Pydantic schemas in a later phase.

## Boundary

The legacy frontend at the repo root (`/src`, served by Vite +
TanStack Start) is **not** part of this pnpm workspace; it manages
its own dependencies through the root `package.json` (held stable
by the freeze contract). New TypeScript packages and apps live
under `packages/ts/*` and `apps/*` and are pnpm-managed.
