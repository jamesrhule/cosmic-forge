"""qcompass-bench CLI.

```
qcompass-bench run [--domain D] [--instance NAME]
qcompass-bench run --suite particle --providers local_aer,ibm
qcompass-bench report [--since 7d]
qcompass-bench leaderboard
```
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Optional

import typer

from .registry import run_benchmark_suite
from .report import render_markdown
from .runner import run_bench
from .store import LeaderboardStore

app = typer.Typer(no_args_is_help=True, add_completion=False)


_DURATION = re.compile(r"^(\d+)([smhdw])$")


def _parse_since(text: str) -> timedelta:
    match = _DURATION.match(text)
    if not match:
        raise typer.BadParameter(
            f"--since must look like '7d', '24h', '30m'; got {text!r}",
        )
    value = int(match.group(1))
    unit = match.group(2)
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86_400, "w": 604_800}[unit]
    return timedelta(seconds=value * multiplier)


@app.command()
def run(
    domain: Optional[str] = typer.Option(
        None, help="Restrict to one registered domain.",
    ),
    instance: Optional[str] = typer.Option(
        None, help="Restrict to one fixture stem (e.g. 'h2').",
    ),
    suite: Optional[str] = typer.Option(
        None,
        help=(
            "Run the bundled-manifest suite for this name "
            "(e.g. 'particle', 'all', a domain). Mutually exclusive "
            "with --domain / --instance."
        ),
    ),
    providers: Optional[str] = typer.Option(
        None,
        help=(
            "Comma-separated provider list (e.g. 'local_aer,ibm') "
            "passed through to run_benchmark_suite when --suite is "
            "set. Phase-1 records the providers in the report."
        ),
    ),
) -> None:
    """Execute the requested fixtures and append them to the leaderboard.

    --suite drives the v2 :func:`run_benchmark_suite` path (bundled
    manifests only, structured Report output). --domain / --instance
    keep the legacy plugin-instance leaderboard path.
    """
    if suite is not None:
        if domain or instance:
            raise typer.BadParameter(
                "--suite is mutually exclusive with --domain / --instance.",
            )
        provider_list = (
            [p.strip() for p in providers.split(",") if p.strip()]
            if providers else None
        )
        report = run_benchmark_suite(suite, providers=provider_list)
        typer.echo(_render_report(report))
        return
    domains = [domain] if domain else None
    rows = run_bench(domains=domains, instance=instance)
    typer.echo(render_markdown(rows))


def _render_report(report) -> str:
    lines = [
        f"# Suite: {report.suite}",
        f"Providers: {', '.join(report.providers)}",
        f"Records: {report.total()} (passed: {report.passed()})",
        "",
        "| fixture_id | domain | provider | status | metric | value | target |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in report.records:
        lines.append(
            f"| {r.fixture_id} | {r.domain} | {r.provider} | {r.status} "
            f"| {r.primary_metric} | {r.primary_value} | {r.target} |",
        )
    return "\n".join(lines)


@app.command()
def report(
    since: Optional[str] = typer.Option(
        "7d", help="Window to render (e.g. 7d, 24h, 30m).",
    ),
) -> None:
    """Render a markdown leaderboard for the given time window."""
    store = LeaderboardStore()
    delta = _parse_since(since) if since else None
    rows = store.recent(since=delta)
    typer.echo(render_markdown(rows))


@app.command()
def leaderboard() -> None:
    """Render every recorded run."""
    store = LeaderboardStore()
    typer.echo(render_markdown(store.all()))


def main() -> None:
    """Entry point referenced by the ``[project.scripts]`` table."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
