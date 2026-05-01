"""Discover qcompass.domains plugins + their bundled fixtures."""

from __future__ import annotations

import importlib.resources as resources
from dataclasses import dataclass
from pathlib import Path

from qcompass_core.registry import get_simulation, list_domains


@dataclass(frozen=True)
class FixtureRef:
    """A bundled fixture in a plugin's ``instances/`` folder."""

    domain: str
    name: str            # filename stem (e.g. "h2")
    path: Path           # absolute path on disk


def list_domain_names() -> list[str]:
    """Pass-through to qcompass_core; surfaces every registered plugin."""
    return list_domains()


def list_fixtures(domain: str) -> list[FixtureRef]:
    """Return every YAML fixture bundled under the plugin's ``instances/``."""
    sim_cls = get_simulation(domain)
    module_name = sim_cls.__module__.split(".")[0]
    package_root = _resolve_instances_dir(module_name)
    if package_root is None:
        return []
    fixtures: list[FixtureRef] = []
    for file in sorted(package_root.glob("*.yaml")):
        fixtures.append(
            FixtureRef(domain=domain, name=file.stem, path=file),
        )
    return fixtures


def _resolve_instances_dir(module_name: str) -> Path | None:
    """Find ``<module>/instances/`` even when it's a namespace package."""
    try:
        anchor = resources.files(module_name)
    except (ModuleNotFoundError, TypeError):
        return None
    candidate = anchor / "instances"
    try:
        if not candidate.is_dir():
            return None
    except (FileNotFoundError, NotADirectoryError):
        return None
    return Path(str(candidate))


def list_all_fixtures(domains: list[str] | None = None) -> list[FixtureRef]:
    """Iterate every domain (or the supplied subset) and gather fixtures."""
    targets = domains if domains is not None else list_domain_names()
    out: list[FixtureRef] = []
    for d in targets:
        if d == "null":
            continue  # built-in test plugin; no instances/.
        out.extend(list_fixtures(d))
    return out


def load_fixture(ref: FixtureRef) -> dict[str, object]:
    """Load a YAML fixture as the plugin's problem payload."""
    import yaml

    return yaml.safe_load(ref.path.read_text())
