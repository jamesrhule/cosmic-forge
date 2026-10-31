"""Path-injection guards for ids that arrive from requests.

Run ids and domain ids become file names under the artifacts roots.
``safe_component`` accepts only a single, conservative path component and
``safe_join`` refuses any result that resolves outside its root (``..``,
absolute paths, symlink escapes). Both raise ``UnsafePathError`` (a
``ValueError``), which HTTP layers map to 400.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_SAFE_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class UnsafePathError(ValueError):
    """An id or path would escape its artifacts root."""


def safe_component(value: str, what: str = "id") -> str:
    """Return ``value`` if it is one safe path component, else raise."""
    if not isinstance(value, str) or not _SAFE_COMPONENT.fullmatch(value) or ".." in value:
        msg = f"invalid {what} {value!r}: use letters, digits, '.', '_' or '-' (no '..', max 128)"
        raise UnsafePathError(msg)
    return value


def safe_join(root: Path | str, *parts: str) -> Path:
    """Join ``parts`` under ``root`` and verify the result stays inside it."""
    base = os.path.realpath(os.fspath(root))
    candidate = os.path.realpath(os.path.join(base, *parts))
    if candidate != base and not candidate.startswith(base + os.sep):
        msg = f"path {os.path.join(*parts)!r} escapes {base!r}"
        raise UnsafePathError(msg)
    return Path(candidate)


__all__ = ["UnsafePathError", "safe_component", "safe_join"]
