"""FCIDUMP reader (Knowles-Handy 1989 format).

Parses the two-line header (NORB, NELEC, MS2, ORBSYM, ISYM) plus the
integral block where each line is ``value  i  j  k  l``. Only enough
of the format to validate inputs; numerical evaluation is left to
plugins (PySCF / openfermion / block2).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from ..errors import HamiltonianFormatError


class FCIDUMP(BaseModel):
    """Parsed FCIDUMP one- and two-electron integrals."""

    model_config = ConfigDict(extra="forbid")

    norb: int = Field(ge=1)
    nelec: int = Field(ge=0)
    ms2: int  # 2*S_z (signed)
    orbsym: list[int] = Field(default_factory=list)
    isym: int = 1
    integrals: list[tuple[float, int, int, int, int]] = Field(default_factory=list)
    nuclear_repulsion: float = 0.0


_HEADER_KV = re.compile(r"(\w+)\s*=\s*([^,/]+?)(?=\s*[,/]|\s*$)", re.IGNORECASE)


def read_fcidump(path: str | Path) -> FCIDUMP:
    """Parse an FCIDUMP file from disk.

    Raises :class:`HamiltonianFormatError` if the header is malformed
    or required fields are missing.
    """
    text = Path(path).read_text()
    return _parse(text.splitlines())


def _parse(lines: Iterable[str]) -> FCIDUMP:
    iterator = iter(lines)
    header_chunks: list[str] = []
    in_header = False
    for raw in iterator:
        line = raw.strip()
        if not line:
            continue
        if not in_header:
            if "&FCI" in line.upper():
                in_header = True
                header_chunks.append(line[line.upper().index("&FCI") + 4:])
            else:
                # Some FCIDUMP variants omit the &FCI marker.
                header_chunks.append(line)
                in_header = True
            continue
        if line.startswith("/") or line.upper().startswith("&END") or line == "&END":
            break
        header_chunks.append(line)

    header_text = ",".join(header_chunks)
    fields = {m.group(1).upper(): m.group(2).strip() for m in _HEADER_KV.finditer(header_text)}
    try:
        norb = int(fields["NORB"])
        nelec = int(fields["NELEC"])
        ms2 = int(fields.get("MS2", "0"))
    except (KeyError, ValueError) as exc:
        msg = f"FCIDUMP header missing required fields (got {fields!r})."
        raise HamiltonianFormatError(msg) from exc

    orbsym = [int(x) for x in re.split(r"[\s,]+", fields.get("ORBSYM", "")) if x]
    isym = int(fields.get("ISYM", 1))

    integrals: list[tuple[float, int, int, int, int]] = []
    nuclear = 0.0
    for raw in iterator:
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            msg = f"Expected 'value i j k l', got {line!r}."
            raise HamiltonianFormatError(msg)
        try:
            value = float(parts[0])
            i, j, k, l_idx = (int(parts[n]) for n in range(1, 5))
        except ValueError as exc:
            msg = f"Bad integral line: {line!r}"
            raise HamiltonianFormatError(msg) from exc
        if (i, j, k, l_idx) == (0, 0, 0, 0):
            nuclear = value
        else:
            integrals.append((value, i, j, k, l_idx))

    return FCIDUMP(
        norb=norb,
        nelec=nelec,
        ms2=ms2,
        orbsym=orbsym,
        isym=isym,
        integrals=integrals,
        nuclear_repulsion=nuclear,
    )


def write_fcidump_stub(_h: FCIDUMP, _path: str | Path) -> None:
    """Stub writer.

    Real serialisation lands when the first qfull-* plugin needs to
    emit FCIDUMPs (qfull-chemistry roadmap, prompt 4). Until then
    callers must use openfermion / pyscf for output.
    """
    msg = "FCIDUMP writing is not yet implemented; use openfermion / pyscf for now."
    raise NotImplementedError(msg)
