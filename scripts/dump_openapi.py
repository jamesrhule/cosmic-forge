"""Write the compute API's OpenAPI document as stable JSON (P4-02).

The FastAPI app (``ucgle_f1.m8_agent.server.build_app``) is the contract
(PLAN Part 4). This builds the app without starting it (no database, no
lifespan) and prints ``app.openapi()`` with sorted keys and a trailing
newline, so the same backend always yields the same bytes.

Usage: ``uv run --frozen python scripts/dump_openapi.py [OUT]`` (stdout when
OUT is omitted). ``scripts/gen_sdk_types.sh`` calls it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    # The document must not depend on the caller's environment: CORS and
    # auth settings are read per request, but pin the mode anyway so a
    # developer's shell can't leak into the committed contract.
    os.environ["QCOMPASS_ENV"] = "production"
    os.environ.pop("QCOMPASS_DEV_ALLOW_ANONYMOUS", None)
    from ucgle_f1.m8_agent.server import build_app

    spec = build_app().openapi()
    text = json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if len(argv) > 1:
        Path(argv[1]).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
