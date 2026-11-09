"""Backend-wide pytest configuration: a real Postgres for every session (P3-01)."""

pytest_plugins = ["ucgle_f1.db.pytest_plugin"]
