# Optional backends that are not installed by an extra

The code imports every optional backend lazily and runs without it. Some backends cannot be extras of
the workspace packages, for one of two reasons.

## Not on a package index

These are distributed only as source repositories, so they cannot be declared as resolvable extras in
`backend/pyproject.toml` (the workspace `uv.lock` must resolve every extra).

| Backend         | Used by                                                           | Upstream                         | Install                                                                                           |
| --------------- | ----------------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------- |
| PyTransport 3.0 | multi-field scalar adapter (`ucgle_f1[multifield]`)               | github.com/Zer095/PyTransport3.0 | clone and follow the upstream build instructions, then `pip install` it into the same environment |
| GWBird          | detector-network sensitivity in `ucgle_f1.m6_gw` (`ucgle_f1[gw]`) | github.com/ilariacaporali/GWBird | `pip install git+https://github.com/ilariacaporali/GWBird`                                        |

Check each upstream licence before redistributing anything built with it (repository licence gate, R11).

## GPL code: separate process only (PLAN R11)

QCompass packages, the SDK, the images and the web bundle contain only permissive or weak-copyleft code.
GPL/AGPL tools may run only as separate processes, never imported into a QCompass process. The backends
below are GPL themselves or hard-require a GPL package, so no extra installs them. Each runs as a separate
process, delivered by the ticket named. Until then the adapter keeps its soft import and its labelled
fallback.

| Backend                    | GPL code (licence, checked on its repository and PyPI page)                                       | Adapter                                                                                | Delivered by                                              | Fallback today                                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| block2 / pyblock2 (DMRG)   | block2 (GPL-3.0-only)                                                                             | `qcompass_core.Block2Adapter`, `qfull_chem.classical` DMRG path, `qfull_nuc.classical` | P2-06 (M13 runner; P2-10 uses it for nuclear)             | `ClassicalReferenceError` naming the separate process; FCI and CCSD(T) via PySCF, nuclear ED up to 8 sites |
| netket (NQS)               | igraph (GPL-2.0, python-igraph), a hard requirement of netket (netket itself is Apache-2.0)       | `qfull_amo.classical`, `qfull_cm.classical`                                            | P2-11 (AMO NQS reference; the same runner serves condmat) | exact diagonalisation up to 14 sites (AMO) and 12 sites (OTOC)                                             |
| Cobaya (inference)         | py-bobyqa (GPL-3.0-or-later), a hard requirement of Cobaya (Cobaya itself is LGPL-3.0)            | `ucgle_f1.m7_infer.inference` (`backend="cobaya"`)                                     | P1-09                                                     | `backend="bilby"` (bilby + dynesty, `ucgle_f1[infer]`)                                                     |
| CosmoGW (Ω_gw, LISA/Taiji) | CosmoGW (GPL: the repository's licence file is GPL-2.0, its README and PyPI classifier say GPLv3) | `ucgle_f1.m6_gw.sgwb`                                                                  | P1-06                                                     | M6 placeholder path                                                                                        |
| PTAfast (PTA overlap)      | healpy (GPL-2.0-only), a hard requirement of PTAfast (PTAfast itself is MIT)                      | `ucgle_f1.m6_gw`                                                                       | P1-06                                                     | none wired yet (P1-06 owns the PTA output)                                                                 |

`qfull-amo[bloqade_digital]` lists the `bloqade` meta-package's components without bloqade-circuit's `vis`
extra. That extra adds matplotlib and tqdm (the only libraries `bloqade.visual` imports, so they are listed
directly), the `ffmpeg` PyPI package (never imported; animation export calls the ffmpeg binary through
matplotlib) and PyQt5 (GPL-3.0, a Qt interactive backend for matplotlib). `import bloqade` and every bloqade
module behave as before; only the Qt interactive window is not installed.

## Servers reached over the network

The `vllm` agent provider (`ucgle_f1.m8_agent.models.local_vllm`) is an HTTP client of a vLLM
OpenAI-compatible server at `$VLLM_URL` (default `http://localhost:8000/v1`) and never imports `vllm`.
Run the server in its own environment or container, at vLLM 0.32.0 or later: every earlier release carries
high or critical advisories (for example GHSA-94f4-hr76-p5j6, GHSA-6757-hggm-hp2w). `ucgle_f1[vllm]` is
kept, empty, so existing install commands still work.
