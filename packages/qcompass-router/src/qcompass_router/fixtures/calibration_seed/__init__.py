"""Synthetic FoMaC calibration histories (PROMPT 6 v2).

These YAMLs feed :func:`qcompass_router.calibration.load_calibration_seed`
so audits + tests can pre-populate the v2 ``devices`` table with a
realistic 7-day history per (provider, backend) without touching
the ~/.cache live cache.

One file per device. Filename stem matches the
:func:`load_calibration_seed` ``name`` argument.
"""
