"""UCGLE-F1 adapters.

Additive surface that lets the M1-M7 pipeline be driven by external
contracts. Today: ``qcompass_core.Simulation`` (see :mod:`.qcompass`).

Importing this subpackage MUST NOT pull in any optional dependency.
The ``qcompass`` adapter is loaded lazily so a base install of
cosmic-forge keeps working when qcompass-core is not installed.
"""

from __future__ import annotations

# Submodules are intentionally NOT eager-imported here. Callers do
# ``from ucgle_f1.adapters.qcompass import LeptogenesisSimulation``
# explicitly when they want the qcompass surface.

__all__: list[str] = []
