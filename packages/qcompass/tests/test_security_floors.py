"""Security floors reach every published wheel (P0-05; PLAN R11, R17).

The workspace lock gets its security floors from the root ``[tool.uv]
constraint-dependencies``. Those never reach a published wheel's metadata, so
without a floor in the member's own ``pyproject.toml``,
``pip install qcompass-router[azure]`` would still resolve azure-quantum
3.13.0, which caps cryptography at the vulnerable 46.0.3.

This test walks ``uv.lock``: every requirement group (base dependencies or an
extra) of every workspace member whose third-party closure reaches a floored
package must declare that floor itself, without a marker. "Floored package"
means every root ``constraint-dependencies`` floor, whatever the advisory's
severity: ``test_every_root_floor_is_checked`` fails when the root gains a floor
that ``FLOORS`` does not list.
"""

from __future__ import annotations

import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

REPO = Path(__file__).resolve().parents[3]

BASE = "<dependencies>"

# Every root constraint floor: the first release that fixes the advisories
# the dependency review found (docs/build/evidence/P0-05-dependency-review.md).
# cryptography and amazon-braket-sdk fix high/critical advisories; setuptools
# fixes a moderate and a low one (GHSA-h35f-9h28-mq5c, GHSA-xmj3-9gf7-h52w);
# virtualenv is not in the lock today, so no group pulls it.
FLOORS: dict[str, Version] = {
    "cryptography": Version("50.0.0"),
    "amazon-braket-sdk": Version("1.117.0"),
    "setuptools": Version("84.1.0"),
    "virtualenv": Version("21.14.9"),
}

# Groups that pull each floored package in today's lock. The walk must find at
# least these, so a broken walk cannot pass by finding nothing.
KNOWN_PULLERS: dict[str, set[tuple[str, str]]] = {
    "cryptography": {
        ("qcompass", "azure"),
        ("qcompass", "ibm"),
        ("qcompass-core", "azure"),
        ("qcompass-core", "ibm"),
        ("qcompass-router", "azure"),
        ("qcompass-router", "ibm"),
        ("qcompass-router", "pasqal"),
        ("qfull-amo", "bloqade-digital"),
        ("qfull-amo", "pasqal"),
        ("qfull-chemistry", "ibm"),
        ("qfull-condmat", "ibm"),
        ("qfull-hep", "ibm"),
        ("qfull-nuclear", "ibm"),
    },
    "amazon-braket-sdk": {
        ("qcompass-router", "braket"),
        ("qcompass-router", "quera"),
        ("qfull-amo", "bloqade-analog"),
        ("qfull-amo", "bloqade-digital"),
        ("qfull-condmat", "analog"),
        ("qfull-hep", "ionq"),
        ("qfull-nuclear", "ionq"),
    },
    # pyscf requires setuptools without a marker.
    "setuptools": {
        ("qcompass", "chem"),
        ("qcompass-core", "chem"),
        ("qfull-chemistry", BASE),
        ("qfull-chemistry", "chem"),
        ("qfull-chemistry", "sqd"),
    },
}


def _manifests() -> dict[str, dict[str, Any]]:
    """Every workspace member (root ``[tool.uv.workspace]``): name -> ``[project]``.

    That covers every packages/*/pyproject.toml and backend/pyproject.toml, and
    any member a later wave adds.
    """
    root = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    workspace = root["tool"]["uv"]["workspace"]
    excluded = {(REPO / e).resolve() for e in workspace.get("exclude", [])}
    out: dict[str, dict[str, Any]] = {}
    for pattern in workspace["members"]:
        for member in sorted(REPO.glob(pattern)):
            path = member / "pyproject.toml"
            if member.resolve() in excluded or not path.is_file():
                continue
            project = tomllib.loads(path.read_text(encoding="utf-8"))["project"]
            out[canonicalize_name(project["name"])] = project
    return out


def test_every_package_manifest_is_scanned() -> None:
    names = set(_manifests())
    for path in [*(REPO / "packages").glob("*/pyproject.toml"), REPO / "backend/pyproject.toml"]:
        project = tomllib.loads(path.read_text(encoding="utf-8"))["project"]
        assert canonicalize_name(project["name"]) in names, f"{path} is not scanned"


def _lock() -> list[dict[str, Any]]:
    return tomllib.loads((REPO / "uv.lock").read_text(encoding="utf-8"))["package"]


def _pulling_groups() -> dict[tuple[str, str, str], list[str]]:
    """(member, group, floored package) -> one dependency path from the lock."""
    packages = _lock()
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in packages:
        by_name[entry["name"]].append(entry)
    members = {e["name"] for e in packages if {"editable", "virtual"} & set(e.get("source", {}))}

    def edges(name: str, extras: tuple[str, ...]) -> list[tuple[str, tuple[str, ...]]]:
        out: list[tuple[str, tuple[str, ...]]] = []
        for entry in by_name[name]:
            deps = list(entry.get("dependencies", []))
            for extra in extras:
                deps += entry.get("optional-dependencies", {}).get(extra, [])
            out += [(d["name"], tuple(d.get("extra", []))) for d in deps]
        return out

    found: dict[tuple[str, str, str], list[str]] = {}
    for member in sorted(members & set(_manifests())):
        entry = by_name[member][0]
        groups = {BASE: entry.get("dependencies", [])}
        groups.update(entry.get("optional-dependencies", {}))
        for group, deps in groups.items():
            stack = [
                ((d["name"], tuple(d.get("extra", []))), [d["name"]])
                for d in deps
                if d["name"] not in members
            ]
            seen: set[tuple[str, tuple[str, ...]]] = set()
            while stack:
                (name, extras), path = stack.pop()
                if (name, extras) in seen or name in members:
                    continue
                seen.add((name, extras))
                if name in FLOORS:
                    found.setdefault((member, group, name), path)
                for nxt in edges(name, extras):
                    stack.append((nxt, [*path, nxt[0]]))
    return found


PULLING = _pulling_groups()


def _lower_bound(req: Requirement) -> Version | None:
    bounds = [
        Version(spec.version)
        for spec in req.specifier
        if spec.operator in {">=", ">", "~=", "==", "==="} and "*" not in spec.version
    ]
    return max(bounds, default=None)


def _declared_floor(project: dict[str, Any], group: str, package: str) -> Version | None:
    if group == BASE:
        reqs = project.get("dependencies", [])
    else:
        extras = {
            canonicalize_name(k): v for k, v in project.get("optional-dependencies", {}).items()
        }
        reqs = extras.get(group, [])
    bounds = [
        bound
        for req in map(Requirement, reqs)
        if canonicalize_name(req.name) == package and req.marker is None
        if (bound := _lower_bound(req)) is not None
    ]
    return max(bounds, default=None)


def test_walk_finds_the_known_pullers() -> None:
    for package, known in KNOWN_PULLERS.items():
        found = {(m, g) for (m, g, p) in PULLING if p == package}
        assert known <= found, f"{package}: lock walk missed {sorted(known - found)}"


@pytest.mark.parametrize(
    ("member", "group", "package"),
    sorted(PULLING),
    ids=[f"{m}[{g}]->{p}" for (m, g, p) in sorted(PULLING)],
)
def test_published_group_declares_the_floor(member: str, group: str, package: str) -> None:
    project = _manifests()[member]
    floor = _declared_floor(project, group, package)
    path = " -> ".join(PULLING[(member, group, package)])
    assert floor is not None and floor >= FLOORS[package], (
        f"{member}[{group}] pulls {path} but does not declare "
        f"'{package}>={FLOORS[package]}' (found lower bound {floor})"
    )


def _root_constraints() -> dict[str, Requirement]:
    root = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return {
        canonicalize_name(req.name): req
        for req in map(Requirement, root["tool"]["uv"]["constraint-dependencies"])
    }


def test_every_root_floor_is_checked() -> None:
    """A floor added to the root constraints is walked like the others."""
    for package, req in _root_constraints().items():
        bound = _lower_bound(req)
        if bound is None:
            continue
        assert package in FLOORS, f"root floor {req} is not in FLOORS"
        assert FLOORS[package] >= bound, f"{package}: FLOORS has {FLOORS[package]} < root {bound}"


def test_root_constraints_keep_the_floors() -> None:
    constraints = _root_constraints()
    for package, floor in FLOORS.items():
        assert package in constraints, f"root constraint-dependencies lost {package}"
        bound = _lower_bound(constraints[package])
        assert bound is not None and bound >= floor, f"{package}: root floor {bound} < {floor}"
