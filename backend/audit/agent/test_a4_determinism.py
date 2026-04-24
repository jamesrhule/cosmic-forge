"""A4 — temperature=0 + fixed seed → identical tool sequences."""

from __future__ import annotations

import hashlib
import json

import pytest

from ucgle_f1.domain import AgentTrace, Couplings, Potential, Reheating, RunConfig
from ucgle_f1.m7_infer.pipeline import RunPipeline


def _cfg() -> RunConfig:
    return RunConfig(
        potential=Potential(kind="starobinsky", params={"M": 1.0e-5}),
        couplings=Couplings(xi=1.0e-3, theta_grav=1.0e-3, f_a=1.0e17,
                            M_star=1.0e18, M1=1.0e12, S_E2=1.0),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13),
        precision="fast",
        agent=AgentTrace(conversationId="c", hypothesisId="h"),
    )


def _fingerprint(pr) -> str:  # type: ignore[no-untyped-def]
    modes = pr.modes
    payload = {
        "k": list(map(float, modes.k)),
        "beta_p": [abs(complex(b)) for b in modes.beta_plus],
        "beta_m": [abs(complex(b)) for b in modes.beta_minus],
        "eta_B": float(pr.eta_B),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@pytest.mark.a_audit
def test_three_trials_identical() -> None:
    prints = {_fingerprint(RunPipeline(seed=0).run(_cfg())) for _ in range(3)}
    assert len(prints) == 1, (
        f"Determinism broken: seed=0 produced {len(prints)} distinct fingerprints"
    )
