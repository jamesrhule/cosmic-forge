# Optional backends that are not installed by an extra

The code imports every optional backend lazily and runs without it. Some backends are not extras of
the workspace packages, for one of the reasons below.

## Not on a package index

These are distributed only as source repositories, so they cannot be declared as resolvable extras in
`backend/pyproject.toml` (the workspace `uv.lock` must resolve every extra).

| Backend         | Used by                                                           | Upstream                         | Install                                                                                           |
| --------------- | ----------------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------- |
| PyTransport 3.0 | multi-field scalar adapter (`ucgle_f1[multifield]`)               | github.com/Zer095/PyTransport3.0 | clone and follow the upstream build instructions, then `pip install` it into the same environment |
| GWBird          | detector-network sensitivity in `ucgle_f1.m6_gw` (`ucgle_f1[gw]`) | github.com/ilariacaporali/GWBird | `pip install git+https://github.com/ilariacaporali/GWBird`                                        |

Check each upstream licence before redistributing anything built with it (repository licence gate, R11).

## GPL code: no extra installs it (PLAN R11)

QCompass packages, the SDK, the images and the web bundle contain only permissive or weak-copyleft code.
GPL/AGPL tools may run only as separate processes. The backends below are GPL themselves or hard-require a
GPL package, so no QCompass extra installs them and no QCompass image ships them. Each gets a
separate-process runner, delivered by the ticket named; none of these runners exists yet.

Until a runner lands, the adapters keep their soft imports (PLAN R2). If you install one of these packages
into your own environment yourself, the adapter imports it into your own Python process. QCompass does not
distribute that combination.

| Backend                    | GPL code (licence, checked on its repository and PyPI page)                                       | Soft import today                                                                                                                                     | Separate-process runner                       | Fallback today                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------- |
| block2 / pyblock2 (DMRG)   | block2 (GPL-3.0-only)                                                                             | `import pyblock2` in `qcompass_core.Block2Adapter`, the `qfull_chem.classical` DMRG path and `qfull_nuc.classical`                                    | P2-06 (M13 runner; P2-10 uses it for nuclear) | `ClassicalReferenceError` naming P2-06; FCI and CCSD(T) via PySCF, nuclear ED up to 8 sites |
| netket (NQS)               | igraph (GPL-2.0, python-igraph), a hard requirement of netket (netket itself is Apache-2.0)       | none: nothing imports netket; `qfull_amo.classical` and `qfull_cm.classical` raise `ClassicalReferenceError` above their exact-diagonalisation limits | P2-11 (AMO; the same runner serves condmat)   | exact diagonalisation up to 14 sites (AMO) and 12 sites (OTOC)                              |
| Cobaya (inference)         | py-bobyqa (GPL-3.0-or-later), a hard requirement of Cobaya (Cobaya itself is LGPL-3.0)            | `from cobaya.run import run` in `ucgle_f1.m7_infer.inference` (`backend="cobaya"`)                                                                    | P1-09                                         | `backend="bilby"` (bilby + dynesty, `ucgle_f1[infer]`)                                      |
| CosmoGW (Ω_gw, LISA/Taiji) | CosmoGW (GPL: the repository's licence file is GPL-2.0, its README and PyPI classifier say GPLv3) | `import CosmoGW` in `ucgle_f1.m6_gw.sgwb` (that branch still returns the placeholder)                                                                 | P1-06                                         | M6 placeholder path                                                                         |
| PTAfast (PTA overlap)      | healpy (GPL-2.0-only), a hard requirement of PTAfast (PTAfast itself is MIT)                      | none: only named in the `ucgle_f1.m6_gw` docstring                                                                                                    | P1-06                                         | none wired yet (P1-06 owns the PTA output)                                                  |

## Other licences R11 does not allow

| Package        | Licence (checked on its PyPI release and repository)                                                                                                                                                                   | Was pulled by                                                                                         | What happens now                                                                                                                                                                                                                                                    |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| qbraid-core    | "qBraid Commercial Software License" (the wheel's `LICENSE`; PyPI says Proprietary): for authorised qBraid customers only, personal, academic and educational use, no commercial use, no distribution of modifications | `qfull-amo[bloqade_digital]` → bloqade-circuit's `qbraid` extra → `qbraid` (Apache-2.0) → qbraid-core | The `qbraid` extra is left out. Only the qBraid target in `bloqade.qbraid` needs it: the target takes a `QbraidProvider` from the `qbraid` package. QCompass never uses that target. If you hold a qBraid licence, install `qbraid` yourself and pass its provider. |
| classy (CLASS) | none granted: no licence file or licence metadata in the PyPI release, none in the `lesgourg/class_public` repository, and a README that only asks for a citation                                                      | `ucgle_f1[cosmo]`                                                                                     | Removed from `[cosmo]`; nothing imports it. CAMB stays in `[cosmo]` for CMB tensor spectra (P1-06 names classy optional next to it). P1-06 checks both licences before wiring them.                                                                                 |

CAMB's code is LGPL-3.0-or-later (weak copyleft) and its documentation GFDL-1.3. Its `LICENCE.txt` adds three
conditions: publications using its results go to arXiv no later than to a journal, confirmed bugs are reported,
and the licence and notices appear on all copies. It stays in `ucgle_f1[cosmo]`; nothing imports it yet.

`qfull-amo[bloqade_digital]` lists the `bloqade` meta-package's components without bloqade-circuit's `vis` and
`qbraid` extras:

- `vis` adds matplotlib and tqdm (the only libraries `bloqade.visual` imports, so they are listed directly),
  the `ffmpeg` PyPI package (never imported; animation export calls the ffmpeg binary through matplotlib) and
  PyQt5 (GPL-3.0, a Qt interactive backend for matplotlib).
- `qbraid` adds qbraid-core (see above).

`import bloqade` and every bloqade module, `bloqade.qbraid` included, import as before: `bloqade.qbraid`
imports `qbraid` only for type checking, and no other bloqade-circuit module imports `bloqade.qbraid` (wheel and
isolated environment checked). Only the Qt interactive window is not installed, and submitting through the qBraid
target needs a `qbraid` provider you install yourself.

## Servers reached over the network

The `vllm` agent provider (`ucgle_f1.m8_agent.models.local_vllm`) is an HTTP client of a vLLM
OpenAI-compatible server at `$VLLM_URL` (default `http://localhost:8000/v1`) and never imports `vllm`.
Run the server in its own environment or container, at vLLM 0.32.0 or later: every earlier release carries
high or critical advisories (for example GHSA-94f4-hr76-p5j6, GHSA-6757-hggm-hp2w). `ucgle_f1[vllm]` is
kept, empty, so existing install commands still work.
