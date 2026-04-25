"""Registry tests: entry-point discovery + in-process override."""

from __future__ import annotations

import pytest

from qcompass_core import (
    BackendRequest,
    Manifest,
    UnknownDomainError,
    get_simulation,
    list_domains,
    register,
    reset_registry,
)
from qcompass_core.null_domain import NullSim


@pytest.fixture(autouse=True)
def _isolate_registry() -> None:
    reset_registry()
    yield
    reset_registry()


def test_null_domain_is_discoverable_via_entrypoints() -> None:
    domains = list_domains()
    assert "null" in domains, f"expected 'null' in {domains}"


def test_get_null_simulation_loads_class() -> None:
    cls = get_simulation("null")
    assert cls is NullSim
    sim = cls()
    manifest = Manifest(
        domain="null",
        version="1.0",
        problem={"label": "noop"},
        backend_request=BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    assert instance.label == "noop"


def test_unknown_domain_raises() -> None:
    with pytest.raises(UnknownDomainError):
        get_simulation("does_not_exist")


def test_in_process_register_and_lookup() -> None:
    class FakeSim:
        def prepare(self, manifest: Manifest) -> object: ...
        def run(self, instance: object, backend: object) -> object: ...
        def validate(self, result: object, reference: object) -> object: ...
        @classmethod
        def manifest_schema(cls) -> dict[str, object]:
            return {}

    register("fake", FakeSim)
    assert "fake" in list_domains()
    assert get_simulation("fake") is FakeSim


def test_register_rejects_duplicates() -> None:
    class A:
        pass

    register("dup", A)
    with pytest.raises(ValueError, match="already registered"):
        register("dup", A)


def test_register_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        register("   ", object)
