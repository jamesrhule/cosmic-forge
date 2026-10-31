# QCompass

Multi-domain quantum + classical research workbench. Built on
the UCGLE-F1 cosmology core (frozen at `ucglef1-v1.0.0`) and
extended with seven additional domain plugins:

| Domain | Plugin | First-class observable |
|---|---|---|
| Cosmology (sGB-CS leptogenesis) | `ucgle_f1` | η_B, F_GB |
| Chemistry | `qfull-chemistry` | classical / quantum energy |
| Condensed matter | `qfull-condmat` | OTOC, A(k, ω) |
| High-energy physics | `qfull-hep` | chiral condensate, string tension |
| Nuclear | `qfull-nuclear` | LNV signature, NCSM matrix elements |
| AMO (Rydberg) | `qfull-amo` | blockade correlations, MIS |
| Gravity (SYK / JT) | `qfull-gravity` | spectral form factor |
| StatMech | `qfull-statmech` | QAE, partition function |

The protocol layer (`qcompass-core`) and the router (`qcompass-
router`) are vendor-neutral. The bench harness (`qcompass-bench`)
runs every bundled fixture through the per-domain plugin's
classical reference and records the leaderboard.

## Quick start

```bash
pip install qcompass[ibm,azure,chem]
python -c "from qcompass import list_domains; print(list_domains())"
```

## Where to go next

- **Architecture** — start with the
  [protocol layer](architecture/core.md), then the
  [router + pricing](architecture/router.md) and
  [Phase-3 verdict pipeline](architecture/bench.md).
- **Domains** — each plugin's docs walk through its kinds, the
  classical reference, and the per-domain S-* audit.
- **Paper** — the arXiv preprint skeleton lives under
  [paper/preprint.md](paper/preprint.md).
