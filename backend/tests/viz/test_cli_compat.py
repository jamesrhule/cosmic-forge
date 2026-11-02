"""Gate 0 review: router-branch (6B) cosmic-forge-viz CLI forms still work."""

from __future__ import annotations

from pathlib import Path

import pytest

from cosmic_forge_viz.cli import main


def test_bake_positional_out_and_seed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pytest.importorskip("zarr")
    store = tmp_path / "hep.zarr"
    assert main(["bake", "hep", "schwinger-1plus1d", "--out", str(store), "--seed", "7", "--total", "5"]) == 0
    assert "baked 5 frames" in capsys.readouterr().out
    assert store.exists()


def test_bake_flag_form_unchanged(tmp_path: Path) -> None:
    assert main(["bake", "--domain", "chemistry", "--run", "r1", "--out-dir", str(tmp_path), "--n-frames", "4"]) == 0
    assert (tmp_path / "r1.json").exists()


def test_bake_requires_domain_and_run() -> None:
    assert main(["bake"]) == 2


def test_serve_accepts_reload_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from cosmic_forge_viz import cli

    seen: dict[str, object] = {}

    def _fake_serve(args: object) -> int:
        seen.update(vars(args))
        return 0

    monkeypatch.setattr(cli, "_serve", _fake_serve)
    assert main(["serve", "--reload", "--port", "9999"]) == 0
    assert seen["reload"] is True
    assert seen["port"] == 9999
