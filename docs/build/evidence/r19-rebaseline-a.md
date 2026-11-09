# R19 rebaseline (a) — JAMES DECISIONS 13(a), 15, 16 (run by the build, Decision 22)

**What changed on the three cosmology pages.** Only the badges these decisions authorise, plus the layout shift they cause:
- the Decision 13(a) badge "Synthetic fixture — not a computed result" for `kawai-kim-natural`;
- the Decision 16 badges for `starobinsky-standard` and `gb-off-control`.

Decision 15's new natural default (f = 2.118624e19 GeV, Λ⁴ = 2.563334027300118e-9) and Decision 17's expression-form snippet are not visible on any R19 page. The Configurator's form column renders collapsed at 1440×900.

**Source of the PNGs (Decision-by-build 2).** CI's own 3-browser job rendered them; nothing was rendered in the sandbox.
- Origin: `playwright (chromium · firefox · webkit)` in run 41502033954 (job 125472089623), head `a835572`. The `playwright-report` artifact is 13168817987.
- Dispatching `e2e-baselines.yml` answers 403 to this session.
- Downloading the artifact needed GitHub's artifact store host. James approved adding `productionresultssa5.blob.core.windows.net` to the session environment's allowed hosts on 2026-11-09.
- The rendered code is unchanged between `a835572` and the rebaseline commit: only docs, evidence and `.github/workflows/freeze-tag.yml` (from main) differ.
- Each test ran 3 attempts (first, retry1, retry2) with identical `-actual.png` bytes, with one exception. Chromium `/visualizer/kawai-kim-natural` produced 2 variants: the anti-aliasing flip the W0-NPM lane had already measured on the pre-upgrade code, well inside the spec's `maxDiffPixelRatio: 0.001`. The majority variant (2 of 3) is used.

**Visible differences, one line per change** (from the diff images in `docs/build/evidence/r19-rebaseline-a/`; regions agree across the three browsers):
- `/`: the badge under "F1 — primary mechanism" (y ≈ 191–214). The formula card and the "Active context" line move down by the badge's height, so the diff covers y 180–559. Nothing else changes.
- `/visualizer`: the badge appears on the `kawai-kim-natural` card (D13a) and on the `starobinsky-standard` and `gb-off-control` cards (D16), y ≈ 249–287. The second and third card rows (`f2-nieh-yan-demo`, `f3-large-N-demo`, `f5-resonance-demo`, `f7-stacked-demo`) move down by that height. Nothing else changes.
- `/visualizer/kawai-kim-natural`: the badge in the toolbar after the run id, which moves "↔" and "Compare with…" right (x 209–646, y 69–90). The six panels are unchanged.

| Baseline | Old SHA-256 | New SHA-256 | Diff vs old (CI) | Diff image |
|---|---|---|---|---|
| `chromium/cosmology-default.png` | `9a1713d93617846845a092faa588457226c538e208b46b60a9478136f5d7475c` | `c74c9586e545d47eb855db08b3e34720c4336c41f00145cee6b5e3e48344610a` | 14533 px; bbox (365,191)–(1052,554) | `r19-rebaseline-a/chromium-cosmology-default-diff.png` |
| `chromium/cosmology-visualizer-index.png` | `cc3efc6fc925f910545e681af5ffbd4b728d8582c09d73ed018e014c99b6de20` | `e5d5adc8cab2a5db1197593b4c566a532215543615050a70dde8d0871f22217d` | 13502 px; bbox (257,249)–(1182,526) | `r19-rebaseline-a/chromium-cosmology-visualizer-index-diff.png` |
| `chromium/cosmology-visualizer-kawai-kim-natural.png` | `efe4e752aae68f57071b309f38573a505adc16754ee0eb9a6449872977d4a56b` | `ae9202387d5f2814f7d77132eb18d97730e7e128d2543f4ae4e73fadfd762ad7` | 1734 px; bbox (209,69)–(646,90) | `r19-rebaseline-a/chromium-cosmology-visualizer-kawai-kim-natural-diff.png` |
| `firefox/cosmology-default.png` | `cd81b0d42840e1086dd8fd89ad7c3e7f5da4127260f81a6dff6e08b9f382c772` | `7400cf5b4651f42b7b7002193acec377dad2a4d3952ec86229214aeda3788307` | 11001 px; bbox (365,191)–(1057,555) | `r19-rebaseline-a/firefox-cosmology-default-diff.png` |
| `firefox/cosmology-visualizer-index.png` | `20c0ea065e2bf3df036893814a59f5ff2166d9d90dfc5e7271ad9c4cbcf3baf8` | `eadae03291102aeed528a30877e4e79b154a6ddd25571141da6a79bd3363d89f` | 10509 px; bbox (257,249)–(1182,527) | `r19-rebaseline-a/firefox-cosmology-visualizer-index-diff.png` |
| `firefox/cosmology-visualizer-kawai-kim-natural.png` | `6ed388dbee3fbbc9716e285bd49a47ed11f88fa76a51347895e8105ce357d40a` | `73bb603c41310c8846d963473a1bbbf4b9318fa4891c30e163250b2dd12687c8` | 1455 px; bbox (208,69)–(646,90) | `r19-rebaseline-a/firefox-cosmology-visualizer-kawai-kim-natural-diff.png` |
| `webkit/cosmology-default.png` | `cd8e5a0c7db36d0219df6801edab591191c4ce7d19c124c8f46f7aab69a121d5` | `45e5183c99d439b7ca78fdc0f4cb979e1e400739abf088e59e35ad8874982a5b` | 11735 px; bbox (365,191)–(1057,555) | `r19-rebaseline-a/webkit-cosmology-default-diff.png` |
| `webkit/cosmology-visualizer-index.png` | `90e1169fc1d789a2b8ca50319a6e12df6b57aac99e6a11d705dd6a3a4f4227f4` | `00f6df5d69474bdbc8de697e858fc0520245cde809ba94da2ba8f8a53e3b678a` | 10070 px; bbox (257,249)–(1182,526) | `r19-rebaseline-a/webkit-cosmology-visualizer-index-diff.png` |
| `webkit/cosmology-visualizer-kawai-kim-natural.png` | `aded516f1f8761312a669cf9ca19c1dffa4905c524ae291aa88439e41b8677fe` | `500ae8953e6b5bbce7fae955402a2475b05f953178d59fb2f4c0492022682ea4` | 1460 px; bbox (209,69)–(646,90) | `r19-rebaseline-a/webkit-cosmology-visualizer-kawai-kim-natural-diff.png` |

`scripts/check_r19.sh` reports 9 PNGs matching `R19.sha256`. The authority is CI's 3-browser job on the pushed head.
