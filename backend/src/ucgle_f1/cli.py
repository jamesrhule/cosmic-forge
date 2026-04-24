"""Entrypoint for ``ucgle-f1`` — the top-level CLI.

Currently a thin dispatcher: ``ucgle-f1 run <cfg.yaml>`` runs the
pipeline and prints a one-line η_B summary. Everything heavier flows
through M8 (``ucgle-f1-agent``).
"""

from __future__ import annotations

import argparse
import json
import sys

from .m7_infer.hydra_cfg import load_config
from .m7_infer.pipeline import RunPipeline, build_run_result


def main() -> None:
    p = argparse.ArgumentParser("ucgle-f1")
    sp = p.add_subparsers(dest="cmd", required=True)

    run_p = sp.add_parser("run", help="Execute one pipeline run from a YAML config")
    run_p.add_argument("config_path")
    run_p.add_argument("--audit", action="store_true", help="emit S1–S15 verdicts")

    args = p.parse_args()
    if args.cmd == "run":
        cfg = load_config(args.config_path)
        pr = RunPipeline(seed=0).run(cfg)
        from .m7_infer.audit import run_audit

        result = build_run_result(
            "cli-run", cfg, pr,
            audit_runner=run_audit if args.audit else None,
        )
        print(json.dumps({
            "eta_B": result.eta_B.value,
            "F_GB": result.F_GB,
            "passed": result.audit.summary.passed,
            "total": result.audit.summary.total,
        }))
        return
    sys.exit(2)
