#!/usr/bin/env python3
"""Licence gate (PLAN.md R11).

Fails when any installed Python distribution or any installed npm package
carries a strong-copyleft, network-copyleft, source-available or unknown
licence. Permissive and weak-copyleft licences (LGPL, MPL, EPL, CDDL) pass.

Usage:
    python scripts/licence_gate.py python            # current interpreter's env
    python scripts/licence_gate.py npm [node_modules] # bun/npm install tree

Exceptions live in ``scripts/licence_allowlist.toml`` as
``"<ecosystem>:<name>" = "<reason>"``; every entry must also have a ledger
entry in ``docs/build/LEDGER.md``.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Matched against the upper-cased licence string. Weak copyleft (LGPL, MPL,
# EPL, CDDL) is allowed, so LGPL must not trip the GPL rule.
_DENY = [
    re.compile(r"(?<![L])\bA?GPL"),
    re.compile(r"GNU (AFFERO )?GENERAL PUBLIC"),
    re.compile(r"\bSSPL\b|SERVER SIDE PUBLIC"),
    re.compile(r"\bBUSL\b|BUSINESS SOURCE"),
    re.compile(r"\bCC[- ]BY[- ]NC|NON-?COMMERCIAL"),
    re.compile(r"\bEUPL\b|\bOSL\b|\bRPL\b|COMMONS CLAUSE|ELASTIC LICENSE"),
    re.compile(r"PROPRIETARY|ALL RIGHTS RESERVED"),
]
_UNKNOWN = {"", "UNKNOWN", "UNLICENSED", "NONE", "SEE LICENSE IN LICENSE", "OTHER/PROPRIETARY LICENSE"}


def _verdict(lic: str) -> str | None:
    up = lic.strip().upper()
    if up in _UNKNOWN:
        return "unknown licence"
    # "GPL-2.0 OR MIT" style expressions pass if any alternative passes.
    alternatives = re.split(r"\s+OR\s+|\s*/\s*", up) if " OR " in up or "/" in up else [up]
    for alt in alternatives:
        if not any(p.search(alt) for p in _DENY):
            return None
    return f"disallowed licence {lic!r}"


def _allowlist() -> dict[str, str]:
    path = ROOT / "scripts" / "licence_allowlist.toml"
    if not path.exists():
        return {}
    return {k: str(v) for k, v in tomllib.loads(path.read_text()).items()}


def _python() -> list[tuple[str, str]]:
    out = []
    for dist in metadata.distributions():
        md = dist.metadata
        name = md.get("Name") or "?"
        lic = md.get("License-Expression") or ""
        if not lic:
            classifiers = [c.split("::")[-1].strip() for c in md.get_all("Classifier") or [] if c.startswith("License ::")]
            lic = " OR ".join(c for c in classifiers if c not in {"OSI Approved"}) or (md.get("License") or "")
            lic = lic.splitlines()[0] if lic else ""
        out.append((name, lic))
    return out


def _npm(root: Path) -> list[tuple[str, str]]:
    out = []
    for pj in root.glob("**/package.json"):
        if "/test/" in str(pj) or "/fixtures/" in str(pj):
            continue
        try:
            data = json.loads(pj.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or "name" not in data or "version" not in data:
            continue
        if pj.parent.parent.name not in {"node_modules"} and not pj.parent.parent.name.startswith("@"):
            continue
        lic = data.get("license", "")
        if isinstance(lic, dict):
            lic = lic.get("type", "")
        if not lic and isinstance(data.get("licenses"), list):
            lic = " OR ".join(str(x.get("type", "")) for x in data["licenses"] if isinstance(x, dict))
        out.append((str(data["name"]), str(lic)))
    return out


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"python", "npm"}:
        print(__doc__)
        return 2
    eco = argv[0]
    pkgs = _python() if eco == "python" else _npm(Path(argv[1] if len(argv) > 1 else ROOT / "node_modules"))
    allow = _allowlist()
    bad = []
    for name, lic in sorted(set(pkgs)):
        why = _verdict(lic)
        if why and f"{eco}:{name}" not in allow:
            bad.append(f"{eco}:{name}: {why}")
    print(f"licence gate ({eco}): {len(set(pkgs))} packages checked, {len(bad)} violations")
    for line in bad:
        print("  " + line)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
