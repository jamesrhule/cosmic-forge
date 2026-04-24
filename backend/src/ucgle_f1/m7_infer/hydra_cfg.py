"""Hydra + OmegaConf config loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omegaconf import DictConfig, OmegaConf

from ..domain import Couplings, Potential, Reheating, RunConfig


def load_config(path: str | Path) -> RunConfig:
    raw: DictConfig = OmegaConf.load(Path(path))  # type: ignore[assignment]
    data: dict[str, Any] = OmegaConf.to_container(raw, resolve=True)  # type: ignore[assignment]
    return RunConfig(
        potential=Potential(**data["potential"]),
        couplings=Couplings(**data["couplings"]),
        reheating=Reheating(**data["reheating"]),
        precision=data.get("precision", "standard"),
        agent=data.get("agent"),
    )


def dump_config(cfg: RunConfig, path: str | Path) -> None:
    Path(path).write_text(OmegaConf.to_yaml(cfg.model_dump(mode="json")))
