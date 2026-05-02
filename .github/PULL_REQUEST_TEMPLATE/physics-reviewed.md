<!--
PROMPT 10 v2 §C — physics-reviewed PR template.

This template MUST be used for any PR that touches
`backend/audit/golden.lock`. The drift-alarm workflow refuses to
merge such a PR unless the `physics-reviewed` label is present;
this template captures the audit trail the reviewer needs.

Pick this template when opening the PR by appending
`?template=physics-reviewed.md` to the PR URL.
-->

## Why this PR moves the freeze

<!-- One paragraph: which calibration / measurement / numerical
fix is the bump anchored to? Cite the V2 benchmark suite + commit
SHA + reproduction command. -->

## V1-V8 recovery — must be ≥ previous

| Recovery | Previous | This PR | Δ | Notes |
|---|---|---|---|---|
| V1 | | | | |
| V2 | | | | |
| V3 | | | | |
| V4 | | | | |
| V5 | | | | |
| V6 | | | | |
| V7 | | | | |
| V8 | | | | |

Reproduction:

```bash
cd backend
PYTHONPATH=src uv run pytest audit -q -m "not slow"
dirhash -i '*.pyc' '__pycache__' '.pytest_cache' \
  --algorithm sha256 backend/audit/physics
```

## S1-S15 changes documented per check

For every per-check delta the bump introduces:

- **S1 — <name>**: <was → is, why>
- **S2 — <name>**: <unchanged | was → is + why>
- **S3 — <name>**: ...
- **S4 — <name>**: ...
- **S5 — <name>**: ...
- **S6 — <name>**: ...
- **S7 — <name>**: ...
- **S8 — <name>**: ...
- **S9 — <name>**: ...
- **S10 — <name>**: ...
- **S11 — <name>**: ...
- **S12 — <name>**: ...
- **S13 — <name>**: ...
- **S14 — <name>**: ...
- **S15 — <name>**: ...

## Sign-off

- [ ] Physics reviewer: <handle> — <date>
- [ ] V1-V8 recovery is ≥ previous on every row.
- [ ] Every changed S-check carries a one-line rationale.
- [ ] `physics-reviewed` label applied (CI blocks otherwise).
- [ ] `acceptance/sprint1-baseline.log` appended with the
      old / new dirhash + reviewer handle.

<!--
Reminder: this is the ONLY supported path through which the
freeze can move. The drift-alarm workflow enforces the label;
merging without it is impossible.
-->
