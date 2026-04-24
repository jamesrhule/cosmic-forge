#!/usr/bin/env python3
"""
Generate seven VisualizationTimeline JSON fixtures + one JSONL stream
for the UCGLE-F1 Workbench Visualizer.

Each timeline is internally consistent with the run it claims to
visualise:
  * lepton_flow.eta_B_running converges to the run's exact eta_B.value
  * the "today" sgwb_snapshot is resampled from the run's spectra.sgwb
  * the gb-off-control timeline shows ~zero chiral asymmetry

Re-run any time with `python scripts/gen_visualizer_fixtures.py`. Output
is deterministic (RNG seeded per timeline).
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "public" / "fixtures" / "runs"
OUT_DIR = ROOT / "public" / "fixtures" / "visualizations"
STREAM_DIR = OUT_DIR / "streams"

N_FRAMES = 240
N_MODES = 24
TAU_RANGE = (-60.0, 5.0)

# Phase boundaries — half-open in code, closed in the wire schema.
PHASES = [
    ("inflation", 0, 139),
    ("gb_window", 140, 179),
    ("reheating", 180, 209),
    ("radiation", 210, 229),
    ("sphaleron", 230, 239),
]

# F-variant -> formula \htmlId targets (matched to public/fixtures/formulas/F1-F7.json).
FORMULA_TERM_IDS: dict[str, list[str]] = {
    "F1": ["xi", "theta_grav", "RtildeR", "S_E2", "M1", "fa", "Mstar"],
    "F2": ["xi", "RtildeR", "Treh", "Mstar"],
    "F3": ["theta_grav", "S_E2", "M1", "fa", "Mstar"],
    "F5": ["dGamma", "Gamma_phi", "Treh", "M1"],
    "F7": ["lambdaHPsi", "Treh", "M1", "Mstar"],
}

# Per-phase active-term subsets (used for the formula-glow panel).
PHASE_TERMS: dict[str, dict[str, list[str]]] = {
    "F1": {
        "inflation": ["xi", "theta_grav"],
        "gb_window": ["xi", "theta_grav", "RtildeR"],
        "reheating": ["S_E2", "M1", "fa"],
        "radiation": ["S_E2", "M1", "fa", "Mstar"],
        "sphaleron": ["M1", "Mstar"],
    },
    "F2": {
        "inflation": ["xi"],
        "gb_window": ["xi", "RtildeR"],
        "reheating": ["RtildeR", "Treh"],
        "radiation": ["Treh", "Mstar"],
        "sphaleron": ["Mstar"],
    },
    "F3": {
        "inflation": ["theta_grav"],
        "gb_window": ["theta_grav", "S_E2"],
        "reheating": ["S_E2", "M1"],
        "radiation": ["M1", "fa"],
        "sphaleron": ["fa", "Mstar"],
    },
    "F5": {
        "inflation": ["Gamma_phi"],
        "gb_window": ["Gamma_phi", "dGamma"],
        "reheating": ["dGamma", "Treh"],
        "radiation": ["Treh", "M1"],
        "sphaleron": ["M1"],
    },
    "F7": {
        "inflation": ["lambdaHPsi"],
        "gb_window": ["lambdaHPsi", "Treh"],
        "reheating": ["Treh", "M1"],
        "radiation": ["M1", "Mstar"],
        "sphaleron": ["Mstar"],
    },
}

# (timeline-id, formula-variant, backing-run-id, eta_B_target, A_max, color_mode,
#  extra_overlays, kk_levels|None, xi_override|None)
SPECS: list[tuple[str, str, str, float, float, str, list[str], list[int] | None, float | None]] = [
    ("kawai-kim-natural",   "F1", "kawai-kim-natural",   6.10e-10, 3.5, "chirality", [],                       None,                None),
    ("starobinsky-standard","F1", "starobinsky-standard",5.78e-10, 3.5, "chirality", [],                       None,                None),
    ("gb-off-control",      "F2", "gb-off-control",      1.02e-14, 1.0, "chirality", ["torsion_overlay"],       None,                0.0),
    ("f2-nieh-yan-demo",    "F2", "kawai-kim-natural",   4.80e-10, 2.8, "chirality", ["torsion_overlay"],       None,                None),
    ("f3-large-N-demo",     "F3", "starobinsky-standard",3.40e-10, 2.4, "kk_level",  ["kk_tower"],              [0, 1, 2, 3, 4],     None),
    ("f5-resonance-demo",   "F5", "kawai-kim-natural",   2.10e-10, 4.0, "resonance", ["resonance_inset"],       [0, 1, 2],           None),
    ("f7-stacked-demo",     "F7", "starobinsky-standard",1.60e-10, 2.0, "condensate",["wormhole_node"],         None,                None),
]

# Frequencies (in Hz) — log grid that matches the runs' spectra.sgwb.f_Hz layout.
K_GRID = np.logspace(-4.0, 2.0, N_MODES)


# ─── helpers ──────────────────────────────────────────────────────────

def fnum(x: float) -> float:
    """Round numerics to 6 sig figs to keep the JSON small."""
    if not math.isfinite(x):
        return x
    if x == 0.0:
        return 0.0
    digits = 6
    mag = math.floor(math.log10(abs(x)))
    factor = 10 ** (digits - 1 - mag)
    return round(x * factor) / factor


def phase_for(frame_idx: int) -> str:
    for name, lo, hi in PHASES:
        if lo <= frame_idx <= hi:
            return name
    return PHASES[-1][0]


def gaussian(x: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def smoothstep(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ─── timeline construction ───────────────────────────────────────────

def build_timeline(
    timeline_id: str,
    formula: str,
    backing_run_id: str,
    eta_b_target: float,
    a_max: float,
    color_mode: str,
    extras: list[str],
    kk_levels: list[int] | None,
    xi_override: float | None,
) -> dict[str, Any]:
    rng = np.random.default_rng(abs(hash(timeline_id)) % (2**32))
    run = json.loads((RUNS_DIR / f"{backing_run_id}.json").read_text())
    cfg = run["config"]
    xi = xi_override if xi_override is not None else cfg["couplings"]["xi"]
    theta = cfg["couplings"]["theta_grav"]

    frame_idx = np.arange(N_FRAMES)
    tau = np.linspace(TAU_RANGE[0], TAU_RANGE[1], N_FRAMES)

    # Window envelope centred on frame 160, width ~20.
    window_env = gaussian(frame_idx.astype(float), mu=160.0, sigma=12.0)
    # Smooth ramp for the running BAU.
    eta_ramp = smoothstep(frame_idx.astype(float), 140.0, 220.0)

    # k-band that experiences the GB tachyonic instability.
    k_band_lo, k_band_hi = 1e-2, 1e1

    # Pre-compute h_+, h_- across all frames for stability (cheap @240 × 24).
    log_k = np.log10(K_GRID)
    h_plus_re = np.zeros((N_FRAMES, N_MODES))
    h_plus_im = np.zeros((N_FRAMES, N_MODES))
    h_minus_re = np.zeros((N_FRAMES, N_MODES))
    h_minus_im = np.zeros((N_FRAMES, N_MODES))
    alpha_minus_beta = np.zeros((N_FRAMES, N_MODES))

    base_phase = rng.uniform(0.0, 2 * math.pi, size=N_MODES)
    decay = np.exp(-0.5 * (log_k - 0.0) ** 2 / 4.0)

    for f in range(N_FRAMES):
        # Carrier oscillation in conformal time, k-dependent frequency.
        omega = 0.6 + 0.4 * log_k
        phase = base_phase + omega * tau[f]
        amp_plus = decay * (1.0 + 0.6 * window_env[f])
        amp_minus = decay * (1.0 - 0.6 * window_env[f] * (xi / max(xi, 1e-30)))
        # If xi == 0, both helicities are symmetric.
        chirality_strength = 1.0 if xi > 0 else 0.0
        amp_minus = decay * (1.0 - 0.6 * window_env[f] * chirality_strength)

        h_plus_re[f] = amp_plus * np.cos(phase)
        h_plus_im[f] = amp_plus * np.sin(phase)
        h_minus_re[f] = amp_minus * np.cos(phase + 0.4)
        h_minus_im[f] = amp_minus * np.sin(phase + 0.4)

        # Bogoliubov asymmetry: zero outside band, ramps to a_max inside.
        in_band = (K_GRID >= k_band_lo) & (K_GRID <= k_band_hi)
        amp_growth = a_max * window_env[f] * eta_ramp[f] * chirality_strength
        alpha_minus_beta[f] = np.where(in_band, amp_growth, 0.05 * amp_growth)

    # B_+ / B_- chiral GB-window magnitudes; xi drives the asymmetry.
    xi_norm = xi / 0.0085  # Kawai-Kim baseline normalisation
    B_total = 0.8 * window_env
    B_plus = B_total * (0.5 + 0.4 * xi_norm)
    B_minus = B_total * (0.5 - 0.4 * xi_norm)
    if xi == 0.0:
        B_plus = np.zeros_like(B_plus)
        B_minus = np.zeros_like(B_minus)
    xi_dot_H = (B_plus + B_minus) * (xi if xi > 0 else 0.0) * 100.0

    # Lepton flow magnitudes (running, monotone toward eta_b_target).
    chiral_gw = 1.2 * window_env * eta_ramp * (xi_norm if xi > 0 else 0.0)
    anomaly = chiral_gw * theta
    washout = 0.15 * smoothstep(frame_idx.astype(float), 220.0, 239.0) * anomaly
    delta_N_L = anomaly - washout
    # Force the final eta_B_running to equal the backing run's eta_B exactly.
    eta_running = eta_b_target * eta_ramp
    eta_running[-1] = eta_b_target

    # Resampled "today" SGWB snapshot from the run's spectra.
    run_f = np.array(run["spectra"]["sgwb"]["f_Hz"], dtype=float)
    run_omega = np.array(run["spectra"]["sgwb"]["Omega_gw"], dtype=float)
    run_chi = np.array(run["spectra"]["sgwb"]["chirality"], dtype=float)
    n_snap = 50
    sample_idx = np.linspace(0, len(run_f) - 1, n_snap).round().astype(int)
    sgwb_today = {
        "f_Hz": [fnum(x) for x in run_f[sample_idx].tolist()],
        "Omega_gw": [fnum(x) for x in run_omega[sample_idx].tolist()],
        "chirality": [fnum(x) for x in run_chi[sample_idx].tolist()],
    }
    # Source-time snapshot: amplified by transfer factor.
    sgwb_source = {
        "f_Hz": sgwb_today["f_Hz"],
        "Omega_gw": [fnum(o * 1e6) for o in sgwb_today["Omega_gw"]],
        "chirality": sgwb_today["chirality"],
    }
    sgwb_postreh = {
        "f_Hz": sgwb_today["f_Hz"],
        "Omega_gw": [fnum(o * 30.0) for o in sgwb_today["Omega_gw"]],
        "chirality": sgwb_today["chirality"],
    }
    snapshot_frames = {30: sgwb_source, 200: sgwb_postreh, 239: sgwb_today}

    # Anomaly integrand attached every 10 frames; running_integral end matches eta_running.
    def make_anomaly(frame: int) -> dict[str, Any]:
        k_arr = K_GRID
        target_total = eta_running[frame]
        # Positive integrand peaked in the GB k-band.
        in_band = (k_arr >= k_band_lo) & (k_arr <= k_band_hi)
        weight = np.where(in_band, 1.0, 0.05) * np.exp(-0.5 * ((np.log10(k_arr) - 0.5) / 1.2) ** 2)
        if weight.sum() <= 0:
            weight = np.ones_like(k_arr)
        integrand = weight / weight.sum() * (target_total if target_total != 0 else 1e-30)
        running = np.cumsum(integrand)
        return {
            "k": [fnum(x) for x in k_arr.tolist()],
            "integrand": [fnum(x) for x in integrand.tolist()],
            "running_integral": [fnum(x) for x in running.tolist()],
            "cutoff": fnum(float(k_arr[-3])),
        }

    # Build the frames.
    frames: list[dict[str, Any]] = []
    for f in range(N_FRAMES):
        ph = phase_for(f)
        modes = []
        for i in range(N_MODES):
            in_window = (
                (140 <= f <= 179)
                and (k_band_lo <= K_GRID[i] <= k_band_hi)
                and (xi > 0)
            )
            sample: dict[str, Any] = {
                "k": fnum(float(K_GRID[i])),
                "h_plus_re": fnum(float(h_plus_re[f, i])),
                "h_plus_im": fnum(float(h_plus_im[f, i])),
                "h_minus_re": fnum(float(h_minus_re[f, i])),
                "h_minus_im": fnum(float(h_minus_im[f, i])),
                "alpha_sq_minus_beta_sq": fnum(float(alpha_minus_beta[f, i])),
                "in_tachyonic_window": bool(in_window),
            }
            if kk_levels is not None:
                sample["kk_level"] = int(kk_levels[i % len(kk_levels)])
            modes.append(sample)

        frame_obj: dict[str, Any] = {
            "tau": fnum(float(tau[f])),
            "t_cosmic_seconds": fnum(float(math.exp(tau[f] + 60.0) * 1e-36)),
            "phase": ph,
            "modes": modes,
            "B_plus": fnum(float(B_plus[f])),
            "B_minus": fnum(float(B_minus[f])),
            "xi_dot_H": fnum(float(xi_dot_H[f])),
            "lepton_flow": {
                "chiral_gw": fnum(float(chiral_gw[f])),
                "anomaly": fnum(float(anomaly[f])),
                "delta_N_L": fnum(float(delta_N_L[f])),
                "eta_B_running": fnum(float(eta_running[f]))
                if f < N_FRAMES - 1
                else float(eta_b_target),
            },
            "active_terms": list(PHASE_TERMS[formula][ph]),
        }
        if f in snapshot_frames:
            frame_obj["sgwb_snapshot"] = snapshot_frames[f]
        if f % 10 == 0:
            frame_obj["anomaly_integrand"] = make_anomaly(f)
        frames.append(frame_obj)

    timeline = {
        "runId": timeline_id,
        "formulaVariant": formula,
        "frames": frames,
        "meta": {
            "durationSeconds": 18.0,
            "tauRange": [TAU_RANGE[0], TAU_RANGE[1]],
            "phaseBoundaries": {name: [lo, hi] for name, lo, hi in PHASES},
            "visualizationHints": {
                "panelEmphasis": {
                    "modes": 0.8 if color_mode != "kk_level" else 0.95,
                    "gb_window": 0.9 if xi > 0 else 0.2,
                    "sgwb": 0.7,
                    "anomaly": 0.6,
                    "lepton": 0.85,
                    "formula": 0.5,
                },
                "particleColorMode": color_mode,
                "extraOverlays": list(extras),
                "formulaTermIds": list(FORMULA_TERM_IDS[formula]),
            },
        },
    }
    return timeline


# ─── invariants ──────────────────────────────────────────────────────

BACKING_RUNS = {"kawai-kim-natural", "starobinsky-standard", "gb-off-control"}


def assert_invariants(timeline: dict[str, Any], spec: tuple) -> None:
    tid, formula, backing_id, eta_target, *_ = spec
    frames = timeline["frames"]
    assert len(frames) == N_FRAMES, f"{tid}: frame count"

    # 1. final eta_B_running matches the target / backing run exactly.
    final_eta = frames[-1]["lepton_flow"]["eta_B_running"]
    if tid in BACKING_RUNS:
        run = json.loads((RUNS_DIR / f"{backing_id}.json").read_text())
        assert math.isclose(final_eta, run["eta_B"]["value"], rel_tol=1e-6, abs_tol=1e-30), (
            f"{tid}: final eta_B_running {final_eta} != run.eta_B.value {run['eta_B']['value']}"
        )
    else:
        assert math.isclose(final_eta, eta_target, rel_tol=0.05), (
            f"{tid}: final eta {final_eta} not within 5% of target {eta_target}"
        )

    # 2. final sgwb_snapshot matches resampled run spectra exactly.
    last_snap = frames[-1].get("sgwb_snapshot")
    assert last_snap is not None, f"{tid}: missing final snapshot"
    run = json.loads((RUNS_DIR / f"{backing_id}.json").read_text())
    run_omega = run["spectra"]["sgwb"]["Omega_gw"]
    sample_idx = np.linspace(0, len(run_omega) - 1, len(last_snap["Omega_gw"])).round().astype(int)
    for i, idx in enumerate(sample_idx):
        assert math.isclose(last_snap["Omega_gw"][i], fnum(run_omega[idx]), rel_tol=1e-5), (
            f"{tid}: final snapshot Omega[{i}] does not match run spectra"
        )

    # 3. phaseBoundaries partition [0, N_FRAMES-1].
    bounds = timeline["meta"]["phaseBoundaries"]
    covered = []
    for _, (lo, hi) in bounds.items():
        covered.append((lo, hi))
    covered.sort()
    assert covered[0][0] == 0
    assert covered[-1][1] == N_FRAMES - 1
    for (a_lo, a_hi), (b_lo, _b_hi) in zip(covered, covered[1:]):
        assert b_lo == a_hi + 1, f"{tid}: phase gap/overlap between {a_lo,a_hi} and {b_lo,_b_hi}"

    # 4. active_terms ⊆ formulaTermIds.
    allowed = set(timeline["meta"]["visualizationHints"]["formulaTermIds"])
    for f in frames:
        for t in f["active_terms"]:
            assert t in allowed, f"{tid}: term {t} not in formulaTermIds"

    # 5. mode count constant.
    counts = {len(f["modes"]) for f in frames}
    assert counts == {N_MODES}, f"{tid}: variable mode count {counts}"

    # 6. gb-off-control: no chiral asymmetry, decoupled BAU.
    if tid == "gb-off-control":
        max_b = max(abs(f["B_plus"] - f["B_minus"]) for f in frames)
        assert max_b < 1e-12, f"gb-off-control: chiral asymmetry leaked ({max_b})"
        # Final eta from the run is 1.02e-14 — small but nonzero.
        assert final_eta < 1e-13, f"gb-off-control: final eta too large ({final_eta})"


# ─── main ────────────────────────────────────────────────────────────

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STREAM_DIR.mkdir(parents=True, exist_ok=True)

    timelines: dict[str, dict[str, Any]] = {}
    for spec in SPECS:
        tid = spec[0]
        timeline = build_timeline(*spec)
        assert_invariants(timeline, spec)
        out_path = OUT_DIR / f"{tid}.json"
        out_path.write_text(json.dumps(timeline, separators=(",", ":")))
        timelines[tid] = timeline
        kb = out_path.stat().st_size / 1024
        print(f"  {tid}.json  ({kb:7.1f} KB)  formula={timeline['formulaVariant']}  "
              f"final η_B={timeline['frames'][-1]['lepton_flow']['eta_B_running']:.3e}")

    # Stream: 60 frames sliced from kawai-kim-natural at every 4th frame.
    base = timelines["kawai-kim-natural"]["frames"]
    stream_frames = [base[i] for i in range(0, N_FRAMES, 4)][:60]
    stream_path = STREAM_DIR / "kawai-kim-live.jsonl"
    with stream_path.open("w") as fh:
        for fr in stream_frames:
            fh.write(json.dumps(fr, separators=(",", ":")) + "\n")
    kb = stream_path.stat().st_size / 1024
    print(f"  streams/kawai-kim-live.jsonl  ({kb:7.1f} KB)  {len(stream_frames)} frames")

    # 7. JSONL stream re-parses cleanly and every line has a phase / modes.
    with stream_path.open() as fh:
        for line_no, line in enumerate(fh):
            obj = json.loads(line)
            assert "phase" in obj and "modes" in obj, f"stream line {line_no} bad"

    print("All invariants passed.")


if __name__ == "__main__":
    main()
