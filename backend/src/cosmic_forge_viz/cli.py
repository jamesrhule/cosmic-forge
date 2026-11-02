"""``cosmic-forge-viz`` CLI.

Usage::

    cosmic-forge-viz bake --domain cosmology --run kawai-kim-natural
    cosmic-forge-viz bake --domain hep --run schwinger-1plus1d --out-dir ./viz/hep
    cosmic-forge-viz bake hep schwinger-1plus1d --out ./hep.zarr --seed 7   # Zarr-only (6B form)
    cosmic-forge-viz demo chemistry demo-run --total 5
    cosmic-forge-viz serve --host 127.0.0.1 --port 8765
    cosmic-forge-viz check

argparse-based (no Typer dependency) so it works in the minimal-deps
CI environment.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .baker import bake_synthetic
from .schema import frame_for_domain

_DOMAINS = ("cosmology", "chemistry", "condmat", "hep", "nuclear", "amo", "gravity", "statmech")


def _bake(args: argparse.Namespace) -> int:
    """Synthetic bake: JSON snapshot + Zarr v3 store (when zarr>=3 is installed).

    The router-branch (6B) form — ``bake DOMAIN RUN_ID --out STORE [--seed N]``
    — writes only the Zarr store at an explicit URI with an explicit seed.
    """
    domain = args.domain or args.domain_pos
    run_id = args.run or args.run_pos
    if not domain or not run_id:
        print("bake needs a domain and run id (--domain/--run or positional)", file=sys.stderr)
        return 2
    if domain not in _DOMAINS:
        print(f"unknown domain {domain!r}; choose from {', '.join(_DOMAINS)}", file=sys.stderr)
        return 2
    if args.out is not None:
        from .baker import bake_timeline
        from .fixtures import stable_seed, synthesize_frames, synthesize_manifest

        seed = args.seed if args.seed is not None else stable_seed(run_id)
        frames = list(synthesize_frames(domain, total_frames=args.n_frames, seed=seed))
        manifest = synthesize_manifest(
            domain=domain, run_id=run_id, total_frames=args.n_frames, seed=seed,
        )
        uri = bake_timeline(frames, args.out, manifest)
        print(f"baked {len(frames)} frames → {uri}")
        return 0
    info = bake_synthetic(
        domain=domain,
        run_id=run_id,
        out_dir=Path(args.out_dir) if args.out_dir else None,
        n_frames=args.n_frames,
        tau_max=args.tau_max,
        formula_variant=args.formula_variant,
    )
    json.dump(info, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _demo(args: argparse.Namespace) -> int:
    """Print synthetic frames as JSON to stdout."""
    from .fixtures import stable_seed, synthesize_frames

    seed = args.seed if args.seed is not None else stable_seed(args.run_id)
    frames = synthesize_frames(args.domain, total_frames=args.total, seed=seed)
    json.dump([f.model_dump(mode="json") for f in frames], sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _serve(args: argparse.Namespace) -> int:  # pragma: no cover - runtime
    try:
        import uvicorn  # type: ignore[import-not-found]
    except ImportError:
        print("uvicorn not installed; install the backend [viz] extras.", file=sys.stderr)
        return 2
    if args.reload:
        # Auto-reload needs an import string; the viz root then comes from
        # $VIZ_ARTIFACTS (set it from --viz-root for the reloaded workers).
        import os

        if args.viz_root:
            os.environ["VIZ_ARTIFACTS"] = str(args.viz_root)
        uvicorn.run(
            "cosmic_forge_viz.server:create_app", factory=True, reload=True,
            host=args.host, port=args.port, log_level="info",
        )
        return 0
    from .server import create_app

    app = create_app(viz_root=Path(args.viz_root) if args.viz_root else None)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _check(args: argparse.Namespace) -> int:
    """Schema sanity check — every per-domain frame class resolves."""
    for domain in _DOMAINS:
        print(f"{domain:>10s} → {frame_for_domain(domain).__name__}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cosmic-forge-viz")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_bake = sub.add_parser("bake", help="Bake a synthetic timeline (JSON + Zarr v3).")
    p_bake.add_argument("domain_pos", nargs="?", metavar="DOMAIN", help="6B positional form")
    p_bake.add_argument("run_pos", nargs="?", metavar="RUN_ID", help="6B positional form")
    p_bake.add_argument("--domain", default=None, choices=_DOMAINS)
    p_bake.add_argument("--run", default=None)
    p_bake.add_argument("--out-dir", default=None)
    p_bake.add_argument("--out", default=None, help="Zarr store URI (6B form: Zarr only)")
    p_bake.add_argument("--seed", type=int, default=None, help="Frame seed (default: stable per run id)")
    p_bake.add_argument("--n-frames", "--total", type=int, default=60)
    p_bake.add_argument("--tau-max", type=float, default=60.0)
    p_bake.add_argument("--formula-variant", default="F1")
    p_bake.set_defaults(handler=_bake)

    p_demo = sub.add_parser("demo", help="Print synthetic frames as JSON.")
    p_demo.add_argument("domain", choices=_DOMAINS)
    p_demo.add_argument("run_id", nargs="?", default="demo")
    p_demo.add_argument("--total", type=int, default=60)
    p_demo.add_argument("--seed", type=int, default=None)
    p_demo.set_defaults(handler=_demo)

    p_serve = sub.add_parser("serve", help="Run the FastAPI service.")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)
    p_serve.add_argument("--viz-root", default=None)
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload (dev).")
    p_serve.set_defaults(handler=_serve)

    p_check = sub.add_parser("check", help="Print the per-domain frame class map.")
    p_check.set_defaults(handler=_check)

    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
