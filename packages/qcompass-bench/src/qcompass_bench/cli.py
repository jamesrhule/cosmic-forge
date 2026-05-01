"""qcompass-bench CLI.

```
qcompass-bench run [--domain D] [--instance NAME]
qcompass-bench report [--since 7d]
qcompass-bench leaderboard
```
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Optional

import typer

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
) -> None:
    """Execute the requested fixtures and append them to the leaderboard."""
    domains = [domain] if domain else None
    rows = run_bench(domains=domains, instance=instance)
    typer.echo(render_markdown(rows))


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
