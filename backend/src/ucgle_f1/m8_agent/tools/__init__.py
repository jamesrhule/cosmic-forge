"""M8 tool surface.

Each file defines typed, idempotent tool functions plus a
``TOOL_SPECS`` list. ``registry.py`` assembles every spec for
``list_tools`` / ``describe_tool`` / ``get_capabilities``.
"""

from __future__ import annotations

from .introspection import TOOL_SPECS as INTROSPECTION_SPECS
from .patch import TOOL_SPECS as PATCH_SPECS
from .research import TOOL_SPECS as RESEARCH_SPECS
from .simulator import TOOL_SPECS as SIMULATOR_SPECS

ALL_TOOL_SPECS = SIMULATOR_SPECS + RESEARCH_SPECS + PATCH_SPECS + INTROSPECTION_SPECS

__all__ = ["ALL_TOOL_SPECS"]
