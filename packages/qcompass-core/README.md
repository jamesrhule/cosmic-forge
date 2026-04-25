# `qcompass-core`

QCompass kernel — domain-agnostic types, schedulers, and capability registry shared by every qfull-* package.

## Status

**Placeholder.** Created during Phase 0 monorepo scaffolding (commit
`ucglef1-v1.0.0`). The real implementation lands in a later phase.

## Why this directory exists today

The QCompass uv workspace at the repo root iterates `packages/*`
and resolves every member via its `pyproject.toml`. Reserving the
package name now keeps imports, entry-points, and CI matrix keys
stable; downstream packages and the `qcompass-router` can already
declare optional dependencies on `qcompass-core` even though it ships no code.

## Boundary

This package MUST NOT import from `ucgle_f1` or any `qfull_*`
sibling. Cross-package coupling flows exclusively through
`qcompass-core` protocols.
