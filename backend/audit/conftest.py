"""Shared fixtures for the S1–S15 and A1–A6 audit suites."""

from __future__ import annotations

import pytest

from ucgle_f1.domain import AgentTrace, Couplings, Potential, Reheating, RunConfig
from ucgle_f1.m7_infer.audit import run_audit
from ucgle_f1.m7_infer.pipeline import RunPipeline


@pytest.fixture(scope="session")
def kawai_kim_config() -> RunConfig:
    """V2 (Kawai-Kim 1702.07689) baseline configuration."""
    return RunConfig(
        potential=Potential(kind="natural", params={"f_a": 1.0, "Lambda": 1.0e-3}),
        couplings=Couplings(
            xi=1.0e-3, theta_grav=1.0e-3, f_a=1.0e17,
            M_star=1.0e18, M1=1.0e12, S_E2=1.0,
        ),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13),
        precision="fast",
        agent=AgentTrace(
            conversationId="conv_audit",
            hypothesisId="hyp_kawai_kim_baseline",
        ),
    )


@pytest.fixture(scope="session")
def gb_off_config() -> RunConfig:
    """GB-off control: xi = 0."""
    return RunConfig(
        potential=Potential(kind="starobinsky", params={"M": 1.0e-5}),
        couplings=Couplings(
            xi=0.0, theta_grav=1.0e-3, f_a=1.0e17,
            M_star=1.0e18, M1=1.0e12, S_E2=1.0,
        ),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13),
        precision="fast",
        agent=AgentTrace(
            conversationId="conv_audit",
            hypothesisId="hyp_gb_off_control",
        ),
    )


@pytest.fixture(scope="session")
def kawai_kim_pipeline(kawai_kim_config):  # type: ignore[no-untyped-def]
    return RunPipeline(seed=0).run(kawai_kim_config)


@pytest.fixture(scope="session")
def gb_off_pipeline(gb_off_config):  # type: ignore[no-untyped-def]
    return RunPipeline(seed=0).run(gb_off_config)


@pytest.fixture(scope="session")
def audit_checks(kawai_kim_pipeline):  # type: ignore[no-untyped-def]
    return {c.id: c for c in run_audit(kawai_kim_pipeline)}
