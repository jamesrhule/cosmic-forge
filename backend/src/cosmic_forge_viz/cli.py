"""``cosmic-forge-viz`` CLI (PROMPT 7 v2 §PART B).

Usage::

    cosmic-forge-viz bake --domain cosmology --run kawai-kim-natural
    cosmic-forge-viz bake --domain hep --run schwinger-1plus1d
    cosmic-forge-viz serve --host 127.0.0.1 --port 8765

The CLI is argparse-based (no Typer dep) so it stays usable in
the minimal-deps environment used by CI smoke tests.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .baker import bake_synthetic
from .schema import frame_class_for_domain


def _bake(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir) if args.out_dir else None
    info = bake_synthetic(
        domain=args.domain,
        run_id=args.run,
        out_dir=out_dir,
        n_frames=args.n_frames,
        tau_max=args.tau_max,
    )
    json.dump(info, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _serve(args: argparse.Namespace) -> int:  # pragma: no cover - runtime
    try:
        import uvicorn  # type: ignore[import-not-found]
    except ImportError:
        print(
            "uvicorn not installed; install backend [viz] extras "
            "(fastapi + uvicorn[standard] + websockets).",
            file=sys.stderr,
        )
        return 2
    from .server import create_app
    app = create_app(viz_root=Path(args.viz_root) if args.viz_root else None)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _check(args: argparse.Namespace) -> int:
    """Schema sanity check — verifies the per-domain frame class loads."""
    for domain in (
        "cosmology", "chemistry", "condmat", "hep", "nuclear", "amo",
    ):
        cls = frame_class_for_domain(domain)
        print(f"{domain:>10s} → {cls.__name__}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cosmic-forge-viz")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_bake = sub.add_parser("bake", help="Bake a synthetic timeline.")
    p_bake.add_argument("--domain", required=True)
    p_bake.add_argument("--run", required=True)
    p_bake.add_argument("--out-dir", default=None)
    p_bake.add_argument("--n-frames", type=int, default=60)
    p_bake.add_argument("--tau-max", type=float, default=60.0)
    p_bake.set_defaults(handler=_bake)

    p_serve = sub.add_parser("serve", help="Run the FastAPI service.")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)
    p_serve.add_argument("--viz-root", default=None)
    p_serve.set_defaults(handler=_serve)

    p_check = sub.add_parser("check", help="Print the per-domain frame class map.")
    p_check.set_defaults(handler=_check)

    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
