"""Global pytest fixtures.

We redirect ``UCGLE_F1_STATE_DIR`` and ``UCGLE_F1_ARTIFACTS`` into a
per-test tmpdir so tests never touch ``~/.ucgle_f1``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path_factory.mktemp("ucgle_state")
    monkeypatch.setenv("UCGLE_F1_STATE_DIR", str(root))
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(root / "artifacts"))
    # Force the memory module to refresh its singleton.
    import ucgle_f1.m8_agent.memory.store as store_mod

    store_mod._store_singleton = None
    _ = Path, os
