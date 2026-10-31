"""Bake per-run visualization timelines to disk.

Two on-disk forms, one writer each (R20):

* **JSON snapshot** ``<root>/<domain>/<run_id>.json`` — a serialized
  :class:`VisualizationTimeline`; what the REST/SSE/WS endpoints and
  the M8 qcompass routes serve.
* **Zarr v3 store** ``<root>/<domain>/<run_id>.zarr`` written by
  :func:`bake_timeline`: scalar timelines as 1-D arrays, phase tags as
  a uint8 index into ``attrs["phase_vocab"]``, per-frame JSON payloads
  as a byte buffer + offsets table, and the manifest under
  ``attrs["manifest_json"]``. Read back with :func:`read_manifest` /
  :func:`read_payloads`.

``zarr`` is soft-imported: :func:`bake_timeline` raises
``RuntimeError`` without it, and :func:`bake_synthetic` then writes the
JSON snapshot only (``zarr_path`` is ``None``).
"""

from __future__ import annotations

import json
import os
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ucgle_f1._paths import safe_component, safe_join

from .fixtures import build_synthetic_timeline
from .phases import progression
from .schema import BaseFrame, VisualizationManifest, VisualizationTimeline


def _default_artifacts_root() -> Path:
    env = os.environ.get("VIZ_ARTIFACTS")
    if env:
        return Path(env)
    return Path.home() / ".qcompass" / "viz"


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


def manifest_for_timeline(
    timeline: VisualizationTimeline, *, bake_uri: str | None = None,
) -> VisualizationManifest:
    """Manifest describing a :class:`VisualizationTimeline`."""
    metadata: dict[str, Any] = {"phases": list(progression(timeline.domain))}
    if timeline.synthetic:
        metadata["synthetic"] = True
    return VisualizationManifest(
        run_id=timeline.run_id,
        domain=timeline.domain,
        frame_count=len(timeline.frames),
        formula_variant=timeline.formula_variant,
        bake_uri=bake_uri,
        metadata=metadata,
    )


def bake_synthetic(
    domain: str,
    run_id: str,
    *,
    out_dir: Path | None = None,
    n_frames: int = 60,
    tau_max: float = 60.0,
    couplings: dict[str, float] | None = None,
    model_domain: str = "1+1D_toy",
    formula_variant: str = "F1",
) -> dict[str, Any]:
    """Bake a synthetic timeline: JSON snapshot plus (if zarr>=3) a Zarr store.

    Returns ``{domain, run_id, json_path, zarr_path, n_frames}``; a Zarr
    failure is non-fatal (``zarr_path`` is ``None``).
    """
    safe_component(domain, "domain")
    safe_component(run_id, "run id")
    out_dir = out_dir or safe_join(_default_artifacts_root(), domain)
    out_dir.mkdir(parents=True, exist_ok=True)

    timeline = build_synthetic_timeline(
        domain, run_id,
        n_frames=n_frames, tau_max=tau_max,
        couplings=couplings, model_domain=model_domain,
        formula_variant=formula_variant,
    )

    json_path = safe_join(out_dir, f"{run_id}.json")
    json_path.write_text(timeline.model_dump_json(indent=2))

    zarr_path: Path | None = safe_join(out_dir, f"{run_id}.zarr")
    try:
        bake_timeline(
            timeline.parsed_frames(),
            zarr_path,
            manifest_for_timeline(timeline, bake_uri=str(zarr_path)),
        )
    except Exception:  # zarr missing (RuntimeError) or a broken install
        zarr_path = None

    return {
        "domain": domain,
        "run_id": run_id,
        "json_path": str(json_path),
        "zarr_path": str(zarr_path) if zarr_path else None,
        "n_frames": len(timeline.frames),
    }


def bake_from_provenance(
    domain: str,
    run_id: str,
    provenance_payload: dict[str, Any],
    *,
    out_dir: Path | None = None,
    n_frames: int = 60,
    tau_max: float = 60.0,
) -> dict[str, Any]:
    """Bake from a provenance sidecar (``POST .../visualization/render``).

    ``manifest.problem.couplings`` and ``model_domain`` drive the
    synthetic builder. Real numerical baking lands when each plugin
    grows a per-frame ``Result.timeline()`` accessor (P4-04).
    """
    manifest = provenance_payload.get("manifest", {})
    problem = manifest.get("problem", {}) if isinstance(manifest, dict) else {}
    couplings = (
        problem.get("couplings")
        if isinstance(problem.get("couplings"), dict) else None
    )
    model_domain = provenance_payload.get("model_domain") or "1+1D_toy"
    return bake_synthetic(
        domain, run_id,
        out_dir=out_dir,
        n_frames=n_frames, tau_max=tau_max,
        couplings=couplings,
        model_domain=str(model_domain),
    )


__all__ = [
    "bake_from_provenance",
    "bake_synthetic",
    "bake_timeline",
    "manifest_for_timeline",
    "read_manifest",
    "read_payloads",
]
