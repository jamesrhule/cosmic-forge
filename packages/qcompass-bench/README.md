# `qcompass-bench`

Leaderboard harness for the QCompass workspace. Iterates every
plugin registered under the `qcompass.domains` entry-point group,
runs each plugin's bundled YAML fixtures through
`prepare → run → validate`, and persists timing + accuracy +
provenance hashes for trend analysis.

## Boundary

This package depends only on `qcompass-core`. It MUST NOT import
from `ucgle_f1` or any `qfull_*` directly — domain discovery flows
through `qcompass_core.registry.list_domains` + `get_simulation`.
Per-domain fixtures are loaded with `importlib.resources` from the
plugin's installed location.

## CLI

```bash
qcompass-bench run                            # all domains
qcompass-bench run --domain chemistry         # one domain
qcompass-bench run --domain chemistry --instance h2
qcompass-bench report --since 7d              # markdown report
qcompass-bench leaderboard                    # full SQLite dump
```

## Leaderboard schema

`~/.qcompass/bench/leaderboard.sqlite`:

```
runs(
    id                 INTEGER PRIMARY KEY,
    domain             TEXT NOT NULL,
    fixture            TEXT NOT NULL,
    package_version    TEXT,
    started_at         TEXT NOT NULL,
    wall_seconds       REAL NOT NULL,
    classical_energy   REAL,
    quantum_energy     REAL,
    provenance_hash    TEXT,
    ok                 INTEGER NOT NULL,
    notes              TEXT
)
```

## Audit (`S-bench-1..3`)

| Check | Description |
|---|---|
| S-bench-1 | Catalogue iterates exactly the domains listed by `qcompass_core.registry.list_domains()`. |
| S-bench-2 | Every successful run records a non-empty `classical_reference_hash` (or the documented `"unavailable"` sentinel). |
| S-bench-3 | `qcompass-bench report` renders without exposing secrets (env vars, file paths under `~/`, API tokens). |

## Tests

```bash
uv run --package qcompass-bench pytest -q
```
