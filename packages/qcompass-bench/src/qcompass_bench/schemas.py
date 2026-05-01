"""FixtureManifest schema (PROMPT 1 v2).

Each YAML under :mod:`qcompass_bench.manifests` validates into one of
these. Bundled-manifest fixtures co-exist with the per-plugin
``instances/`` fixtures discovered by :mod:`catalogue`; the unified
view is exposed by :func:`qcompass_bench.list_all_fixtures`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SuiteDomain = Literal[
    "cosmology",
    "chemistry",
    "condmat",
    "hep",
    "nuclear",
    "amo",
    "gravity",
    "statmech",
]

FixtureKind = Literal[
    "bundled_manifest",   # YAML shipped under qcompass_bench/manifests/
    "plugin_instance",    # bundled YAML inside a qfull-* package
    "external_runner",    # mqt.bench / SupermarQ / QED-C App-Oriented
]


class NumericalBudget(BaseModel):
    """Acceptance-target a fixture pins for its primary observable.

    PROMPT 1 v2 calls these "numerical budgets". Every bundled
    manifest ships one even if the value is qualitative (a string
    target instead of a float tolerance). The bench runner uses
    the budget to mark a fixture pass / degraded / fail.
    """

    model_config = ConfigDict(extra="forbid")

    metric: str = Field(
        description="Free-form name of the observable, e.g. 'eta_B'.",
    )
    target: float | str = Field(
        description=(
            "Numeric target (when the observable is a real-valued "
            "scalar) or string description (qualitative)."
        ),
    )
    tolerance: float | None = Field(
        default=None,
        description=(
            "Absolute tolerance for numeric targets; None for "
            "qualitative ones."
        ),
    )
    relative: bool = Field(
        default=False,
        description=(
            "When True, ``tolerance`` is fractional (|x - target| / "
            "|target|) rather than absolute."
        ),
    )
    notes: str = ""


class FixtureManifest(BaseModel):
    """Validated descriptor of a single benchmark fixture."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        pattern=r"^[a-z0-9][A-Za-z0-9_\-]*$",
        description=(
            "Stable identifier used by qcompass-bench's CLI and the "
            "leaderboard store. Mostly lowercase + dashes/underscores; "
            "uppercase is allowed mid-id for canonical names like "
            "'zN-toy'."
        ),
    )
    name: str = Field(
        description=(
            "Human-readable label. The frontend's leaderboard view "
            "renders this. Default to ``id`` if absent."
        ),
    )
    domain: SuiteDomain
    kind: FixtureKind
    description: str = ""
    qcompass_simulation: str = Field(
        description=(
            "Entry-point name resolvable by "
            "qcompass_core.registry.get_simulation, "
            "e.g. 'cosmology.ucglef1' or 'chemistry'."
        ),
    )
    payload_path: str | None = Field(
        default=None,
        description=(
            "Relative path to a YAML / JSON file the manifest "
            "delegates to (used by bundled cosmology manifests "
            "that point at the cosmic-forge run fixtures)."
        ),
    )
    payload_inline: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Inline payload — used when the manifest IS the "
            "Manifest.problem dict (no external file)."
        ),
    )
    budget: NumericalBudget
    references: list[str] = Field(
        default_factory=list,
        description="arXiv IDs / DOIs anchoring the budget.",
    )

    @field_validator("name")
    @classmethod
    def _name_falls_back_to_id(cls, v: str) -> str:
        return v or ""

    @field_validator("payload_inline")
    @classmethod
    def _exclusive_payload(
        cls,
        v: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return v
