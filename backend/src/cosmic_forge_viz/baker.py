"""Zarr 3 timeline writer.

Bakes a sequence of `BaseFrame` objects into a Zarr v3 store, plus a
sidecar `manifest.json`. The store layout keeps each scalar timeline
field as a 1-D array and stores variable-shape per-frame payloads
(modes, lattice, plaquettes, …) as JSON inside a single object array
group. That trades absolute Zarr-friendliness for a single-pass
writer that doesn't need per-domain ragged-array specialization.

`zarr` is soft-imported inside the call so the package can be used for
schema-only consumers (frontend type generation, fixture-only tests)
without dragging in the Zarr dependency.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Sequence

from cosmic_forge_viz.schema import BaseFrame, VisualizationManifest

_SCALAR_FIELDS = (
    "tau",
    "B_plus",
    "B_minus",
    "xi_dot_H",
    "t_cosmic_seconds",
    "iteration",
    "chiral_condensate",
    "string_tension",
)


def bake_timeline(
    frames: Sequence[BaseFrame],
    store_uri: str | Path,
    manifest: VisualizationManifest,
) -> str:
    """Write `frames` + `manifest` to a Zarr v3 store at `store_uri`.

    Returns the canonical store URI string. Overwrites any existing
    store at the same path. Raises `RuntimeError` if `zarr>=3` is not
    installed.
    """

    try:
        import zarr  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised via importorskip
        raise RuntimeError(
            "cosmic_forge_viz.baker requires `zarr>=3`; install via `pip install cosmic-forge[viz]`"
        ) from exc

    path = Path(store_uri)
    path.mkdir(parents=True, exist_ok=True)

    # Zarr 3 currently flags variable-shape string dtypes as unstable
    # for the v3 spec; we accept that risk for an internal bake format.
    with warnings.catch_warnings():
        try:
            from zarr.errors import UnstableSpecificationWarning  # type: ignore[import-not-found]
            warnings.simplefilter("ignore", UnstableSpecificationWarning)
        except ImportError:  # pragma: no cover
            warnings.simplefilter("ignore")

        root = zarr.open_group(store=str(path), mode="w", zarr_format=3)
        root.attrs["domain"] = manifest.domain
        root.attrs["run_id"] = manifest.run_id
        root.attrs["frame_count"] = manifest.frame_count
        if manifest.formula_variant is not None:
            root.attrs["formula_variant"] = manifest.formula_variant
        # Full manifest stored as a JSON string under attrs so a baked
        # store is self-contained without sidecar files (zarr 3 walks
        # the root directory and warns on unrecognized files).
        root.attrs["manifest_json"] = manifest.model_dump_json()

        n = len(frames)
        if n > 0:
            # Phase tags as a small integer index into a `phase_vocab`
            # attribute. Avoids the still-unstable v3 string dtypes.
            phase_vocab: list[str] = []
            phase_indices: list[int] = []
            for f in frames:
                if f.phase not in phase_vocab:
                    phase_vocab.append(f.phase)
                phase_indices.append(phase_vocab.index(f.phase))
            root.attrs["phase_vocab"] = phase_vocab

            phase_arr = root.create_array(
                name="phase",
                shape=(n,),
                dtype="uint8",
                chunks=(min(n, 256),),
            )
            phase_arr[:] = phase_indices

            # Scalar-per-frame timelines. We populate only fields present
            # on the first frame; all frames in a baked run share a
            # domain, so the field set is uniform.
            sample = frames[0].model_dump()
            for field in _SCALAR_FIELDS:
                if field not in sample:
                    continue
                arr = root.create_array(
                    name=field,
                    shape=(n,),
                    dtype="float64",
                    chunks=(min(n, 256),),
                )
                arr[:] = [float(getattr(f, field, 0.0) or 0.0) for f in frames]

            # Per-frame JSON payloads concatenated into a single byte
            # buffer + a (n,) offsets table. This keeps the v3 array
            # dtypes numeric-stable while still allowing per-frame
            # rehydration.
            payload_blobs = [
                json.dumps(f.model_dump(mode="json")).encode("utf-8") for f in frames
            ]
            offsets: list[int] = []
            cursor = 0
            for blob in payload_blobs:
                offsets.append(cursor)
                cursor += len(blob)
            offsets.append(cursor)

            offsets_arr = root.create_array(
                name="payload_offsets",
                shape=(n + 1,),
                dtype="uint64",
                chunks=(min(n + 1, 256),),
            )
            offsets_arr[:] = offsets

            blob_buf = b"".join(payload_blobs)
            payloads_arr = root.create_array(
                name="payloads",
                shape=(len(blob_buf),),
                dtype="uint8",
                chunks=(max(1, min(len(blob_buf), 1 << 20)),),
            )
            if blob_buf:
                payloads_arr[:] = list(blob_buf)

    return str(path)


def read_manifest(store_uri: str | Path) -> VisualizationManifest:
    """Read the manifest stored under the baked group's attrs."""
    import zarr  # type: ignore[import-not-found]

    group = zarr.open_group(str(store_uri), mode="r", zarr_format=3)
    raw = group.attrs.get("manifest_json")
    if raw is None:
        raise FileNotFoundError(f"no manifest stored at {store_uri!r}")
    return VisualizationManifest.model_validate_json(str(raw))


def read_payloads(store_uri: str | Path) -> list[dict]:
    """Read per-frame JSON payloads back out of a baked store."""
    import zarr  # type: ignore[import-not-found]

    group = zarr.open_group(str(store_uri), mode="r", zarr_format=3)
    if "payloads" not in list(group.array_keys()):
        return []
    offsets = list(map(int, group["payload_offsets"][:]))
    blob = bytes(bytearray(int(b) for b in group["payloads"][:]))
    out: list[dict] = []
    for i in range(len(offsets) - 1):
        chunk = blob[offsets[i] : offsets[i + 1]]
        if not chunk:
            continue
        out.append(json.loads(chunk.decode("utf-8")))
    return out


__all__ = ["bake_timeline", "read_manifest", "read_payloads"]
