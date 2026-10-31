"""msgpack frame round-trip (skipped when ormsgpack absent)."""

from __future__ import annotations

import pytest

from cosmic_forge_viz.fixtures import synthesize_frames
from cosmic_forge_viz.protocol import decode_frame, encode_frame, has_msgpack


@pytest.mark.parametrize(
    "domain", ["cosmology", "chemistry", "condmat", "hep", "nuclear", "amo"]
)
def test_frame_roundtrip(domain: str) -> None:
    frames = synthesize_frames(domain, total_frames=3, seed=1)
    for f in frames:
        wire = encode_frame(f)
        decoded = decode_frame(wire)
        assert decoded.domain == f.domain
        assert decoded.phase == f.phase
        assert decoded.tau == pytest.approx(f.tau)


def test_msgpack_path_when_available() -> None:
    if not has_msgpack():
        pytest.skip("ormsgpack not installed")
    frames = synthesize_frames("cosmology", total_frames=2, seed=0)
    wire = encode_frame(frames[0])
    # msgpack first byte is a fixmap (0x80–0x8f), fixarray, or extension.
    # It is never `{` (0x7B), which would mean JSON fallback.
    assert wire[0] != ord("{")
