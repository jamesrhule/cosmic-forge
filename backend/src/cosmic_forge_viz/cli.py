"""`cosmic-forge-viz` typer CLI: serve, bake, demo.

Soft-imports `typer` and `uvicorn` inside command bodies so the
package is importable for schema-only consumers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _typer() -> Any:
    try:
        import typer  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "cosmic-forge-viz CLI requires the `viz` extras "
            "(`pip install cosmic-forge[viz]`)."
        ) from exc
    return typer


def _build_app() -> Any:
    typer = _typer()
    app = typer.Typer(
        add_completion=False,
        help="Cross-domain visualization streaming for the cosmic-forge stack.",
    )

    @app.command()
    def serve(
        host: str = typer.Option("127.0.0.1", help="Bind host."),
        port: int = typer.Option(8765, help="Bind port."),
        reload: bool = typer.Option(False, help="Enable auto-reload."),
    ) -> None:
        """Run the FastAPI viz server via uvicorn."""
        try:
            import uvicorn  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise SystemExit("`uvicorn` not installed") from exc
        uvicorn.run(
            "cosmic_forge_viz.server:create_app",
            host=host,
            port=port,
            reload=reload,
            factory=True,
        )

    @app.command()
    def bake(
        domain: str = typer.Argument(..., help="Domain tag."),
        run_id: str = typer.Argument(..., help="Run ID."),
        out: Path = typer.Option(..., help="Output store URI / directory."),
        total: int = typer.Option(60, min=1, max=2000),
        seed: int = typer.Option(0),
    ) -> None:
        """Bake a synthetic run to a Zarr v3 store."""
        from cosmic_forge_viz.baker import bake_timeline
        from cosmic_forge_viz.fixtures import synthesize_frames, synthesize_manifest

        frames = list(synthesize_frames(domain, total_frames=total, seed=seed))
        manifest = synthesize_manifest(
            domain=domain, run_id=run_id, total_frames=total, seed=seed
        )
        uri = bake_timeline(frames, out, manifest)
        typer.echo(f"baked {len(frames)} frames → {uri}")

    @app.command()
    def demo(
        domain: str = typer.Argument(..., help="Domain tag."),
        run_id: str = typer.Argument("demo", help="Run ID."),
        total: int = typer.Option(60, min=1, max=2000),
    ) -> None:
        """Print synthetic frames as JSON to stdout."""
        from cosmic_forge_viz.fixtures import synthesize_frames

        frames = list(synthesize_frames(domain, total_frames=total, seed=hash(run_id) & 0xFFFFFFFF))
        typer.echo(json.dumps([f.model_dump(mode="json") for f in frames], indent=2))

    return app


def main() -> None:
    """Console-script entry point."""
    _build_app()()


if __name__ == "__main__":  # pragma: no cover
    main()
