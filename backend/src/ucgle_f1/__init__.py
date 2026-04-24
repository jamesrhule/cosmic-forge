"""UCGLE-F1 — scalar-Gauss-Bonnet-Chern-Simons leptogenesis simulator."""

from __future__ import annotations

__version__ = "0.1.0"

# JAX float64 must be set before any JAX array is created.
# We guard the import because JAX is an optional extra.
try:  # pragma: no cover - environment dependent
    import jax

    jax.config.update("jax_enable_x64", True)
except ImportError:
    pass
