"""Static pricing lookup. Replaced by live pricing in PROMPT 6B."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Search order:
#   1. fixtures shipped inside the wheel (`qcompass_router/fixtures/...`)
#   2. fixtures next to the source tree (editable installs / repo checkout)
_PKG_DIR = Path(__file__).resolve().parent
_CANDIDATES = (
    _PKG_DIR / "fixtures" / "pricing_seed.yaml",
    _PKG_DIR.parent.parent / "fixtures" / "pricing_seed.yaml",
)


def _load_seed() -> dict[str, Any]:
    for path in _CANDIDATES:
        if path.is_file():
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            return data.get("providers", {})
    raise FileNotFoundError(
        "qcompass-router pricing_seed.yaml not found; checked: "
        + ", ".join(str(p) for p in _CANDIDATES)
    )


_SEED: dict[str, dict[str, Any]] = _load_seed()


def _lookup(provider: str, backend: str) -> dict[str, Any]:
    """Resolve a (provider, backend) pair to a seed entry.

    Tries (in order): "<provider>_<backend>", "<backend>", "<provider>".
    """
    candidates: list[str] = []
    if provider and backend:
        candidates.append(f"{provider}_{backend}")
    if backend:
        candidates.append(backend)
    if provider:
        candidates.append(provider)
    for key in candidates:
        if key in _SEED:
            return _SEED[key]
    raise KeyError(
        f"no pricing seed entry for provider={provider!r} backend={backend!r}; "
        f"tried keys: {candidates}"
    )


def estimate(provider: str, backend: str, shots: int) -> float:
    """Return a stub USD cost estimate for `shots` shots on (provider, backend).

    The seed YAML uses a small set of pricing shapes; this function applies
    whichever one matches. Free local backends return 0.0. Phase-6B replaces
    this with real, calibration-aware pricing.
    """
    if shots < 0:
        raise ValueError("shots must be non-negative")

    entry = _lookup(provider, backend)

    # Local / free.
    per_shot = entry.get("per_shot_usd")
    per_task = entry.get("per_task_usd")
    per_run = entry.get("per_run_usd")
    per_second = entry.get("per_second_usd")
    per_credit = entry.get("per_credit_usd")
    per_1q = entry.get("per_1q_shot_usd")
    per_2q = entry.get("per_2q_shot_usd")
    min_program = entry.get("min_program_usd", 0.0)
    hqc_per_circuit = entry.get("hqc_per_circuit")
    hqc_overage_usd = entry.get("hqc_overage_usd")

    cost = 0.0

    if per_1q is not None or per_2q is not None:
        # Azure-style 1q/2q shot pricing. Without circuit analysis we
        # fall back to the 1q rate; PROMPT 6B will count gates.
        rate = float(per_1q if per_1q is not None else (per_2q or 0.0))
        cost = rate * shots
        cost = max(cost, float(min_program))
        return cost

    if hqc_per_circuit is not None and hqc_overage_usd is not None:
        # Quantinuum HQC: one circuit, fixed HQC count, paid as overage.
        cost = float(hqc_per_circuit) * float(hqc_overage_usd)
        return cost

    if per_second is not None:
        # IBM-style per-second billing. Stub: assume 1 ms / shot.
        cost = float(per_second) * (shots * 1e-3)
        return cost

    if per_credit is not None:
        # IQM-style credit billing. Stub: 1 credit per 1000 shots.
        credits = max(1.0, shots / 1000.0)
        cost = float(per_credit) * credits
        return cost

    if per_run is not None:
        cost = float(per_run)
        return cost

    if per_shot is not None or per_task is not None:
        cost = float(per_task or 0.0) + float(per_shot or 0.0) * shots
        return cost

    return 0.0
