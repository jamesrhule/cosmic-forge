# Optional research backends not on a package index

Two optional UCGLE-F1 backends are distributed only as source repositories, so they cannot be
declared as resolvable extras in `backend/pyproject.toml` (the workspace `uv.lock` must resolve every
extra). The code imports them lazily and runs without them.

| Backend         | Used by                                                           | Upstream                         | Install                                                                                           |
| --------------- | ----------------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------- |
| PyTransport 3.0 | multi-field scalar adapter (`ucgle_f1[multifield]`)               | github.com/Zer095/PyTransport3.0 | clone and follow the upstream build instructions, then `pip install` it into the same environment |
| GWBird          | detector-network sensitivity in `ucgle_f1.m6_gw` (`ucgle_f1[gw]`) | github.com/ilariacaporali/GWBird | `pip install git+https://github.com/ilariacaporali/GWBird`                                        |

Check each upstream licence before redistributing anything built with it (repository licence gate, R11).
