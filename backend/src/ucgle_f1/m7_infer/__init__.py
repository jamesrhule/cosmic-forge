"""M7 — Pipeline orchestration, config, inference, and docs.

- Hydra + OmegaConf: config loading in ``hydra_cfg.py``.
- Cobaya / bilby: posterior inference in ``inference.py``.
- ``pipeline.py`` is the M1→M2→M3→M4→M5→M6 driver that every agent
  run uses. It returns a fully populated ``RunResult``.
"""

from __future__ import annotations

from .pipeline import PipelineResult, RunPipeline, build_run_result

__all__ = ["PipelineResult", "RunPipeline", "build_run_result"]
