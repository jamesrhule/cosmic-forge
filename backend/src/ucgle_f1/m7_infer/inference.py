"""Posterior inference wrappers (Cobaya / bilby+dynesty)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class PosteriorRequest:
    log_likelihood: Callable[..., float]
    prior_bounds: dict[str, tuple[float, float]]
    nsamples: int = 2000
    backend: str = "bilby"  # "bilby" | "cobaya"


def run_posterior(req: PosteriorRequest) -> dict[str, Any]:
    if req.backend == "bilby":
        try:
            import bilby  # type: ignore[import-untyped]
            import bilby.core.prior as prior_mod  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError("install extra 'infer' for bilby backend") from exc
        priors = {
            name: prior_mod.Uniform(lo, hi, name=name)
            for name, (lo, hi) in req.prior_bounds.items()
        }

        class _L(bilby.Likelihood):  # type: ignore[misc]
            def __init__(self) -> None:
                super().__init__(parameters={k: 0.0 for k in priors})

            def log_likelihood(self) -> float:
                return float(req.log_likelihood(**self.parameters))

        result = bilby.run_sampler(
            likelihood=_L(),
            priors=priors,
            sampler="dynesty",
            nlive=req.nsamples,
            outdir="/tmp/bilby_out",
            label="ucgle-f1",
        )
        return {"samples": result.posterior.to_dict(orient="list")}

    if req.backend == "cobaya":
        try:
            from cobaya.run import run as cobaya_run  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("install extra 'infer' for cobaya backend") from exc
        info = {
            "likelihood": {"ucgle": {"external": req.log_likelihood}},
            "params": {
                name: {"prior": {"min": lo, "max": hi}}
                for name, (lo, hi) in req.prior_bounds.items()
            },
            "sampler": {"mcmc": {"max_samples": req.nsamples}},
        }
        updated, sampler = cobaya_run(info)
        return {"updated_info": updated, "samples": sampler.samples().data}

    raise ValueError(f"Unknown inference backend: {req.backend}")
