/**
 * UCGLE-F1 Workbench — Visualizer types.
 *
 * Additive contract for the time-evolving visualization layer. Backend
 * (Claude Code) will mirror these as Pydantic models. Field names,
 * casing, enum values, and nesting MUST stay byte-for-byte identical
 * with the JSON the simulator emits.
 *
 * This module deliberately does NOT modify `src/types/domain.ts`. The
 * `formula_variant` is held on the timeline (see VisualizationTimeline)
 * rather than being added to RunConfig; once the simulator is wired in,
 * the field will move onto RunConfig and the timeline will read it
 * through.
 */

/** Which F-formula the timeline visualizes. */
export type FormulaVariant = "F1" | "F2" | "F3" | "F4" | "F5" | "F6" | "F7";

/** Coarse-grained cosmological phase tag attached to each frame. */
export type Phase = "inflation" | "gb_window" | "reheating" | "radiation" | "sphaleron";

/** Visualizer playback mode. */
export type ComparisonMode = "single" | "ab_overlay" | "split_screen";

/** How Panel 1 colours its particles, driven by the formula variant. */
export type ParticleColorMode = "chirality" | "kk_level" | "condensate" | "resonance";

/** Render quality tier for `renderVisualization`. */
export type RenderResolution = "low" | "medium" | "high";

/* ─────────────────────────────────────────────────────────────────────
 * Per-frame data
 * ────────────────────────────────────────────────────────────────── */

/** A single k-mode sample inside one frame. */
export interface VisualizationModeSample {
  /** Comoving wavenumber. */
  k: number;
  h_plus_re: number;
  h_plus_im: number;
  h_minus_re: number;
  h_minus_im: number;
  /** Bogoliubov asymmetry; particle trail length is proportional to this. */
  alpha_sq_minus_beta_sq: number;
  /** True if this k-mode is currently inside the GB tachyonic window. */
  in_tachyonic_window: boolean;
  /** Kaluza-Klein level (F3/F5 variants only). */
  kk_level?: number;
}

/** SGWB snapshot at a specific instant (source / post-reheat / today). */
export interface SgwbSnapshot {
  f_Hz: number[];
  Omega_gw: number[];
  /** Per-frequency chirality, in [-1, +1]. */
  chirality: number[];
}

/** Anomaly integrand vs. k for the current frame. */
export interface AnomalyIntegrandSample {
  k: number[];
  integrand: number[];
  /** Cumulative integral of `integrand` up to each k. */
  running_integral: number[];
  /** Minimal-subtraction cutoff drawn as a vertical line. */
  cutoff: number;
}

/** Sankey flow magnitudes for the four-node lepton flow panel. */
export interface LeptonFlow {
  chiral_gw: number;
  anomaly: number;
  delta_N_L: number;
  /** Running η_B at this frame; final frame matches `RunResult.eta_B.value`. */
  eta_B_running: number;
}

/** A single frame of the visualization timeline. */
export interface VisualizationFrame {
  /** Conformal time. */
  tau: number;
  /** Cosmic time in seconds (for human-readable scrubber labels). */
  t_cosmic_seconds: number;
  phase: Phase;
  modes: VisualizationModeSample[];
  /** Panel 2 — chiral GB window magnitudes. */
  B_plus: number;
  B_minus: number;
  /** GB-instability driver. */
  xi_dot_H: number;
  /** Optional: present at a small subset of frames (snapshot moments). */
  sgwb_snapshot?: SgwbSnapshot;
  /** Optional: present once per ~10 frames to bound payload size. */
  anomaly_integrand?: AnomalyIntegrandSample;
  lepton_flow: LeptonFlow;
  /** \htmlId targets in Panel 6 that should glow at this frame. */
  active_terms: string[];
}

/* ─────────────────────────────────────────────────────────────────────
 * Timeline metadata
 * ────────────────────────────────────────────────────────────────── */

/**
 * Per-formula presentation hints. Computed server-side; the frontend
 * reads them and applies layout/color directives — never invents them.
 */
export interface VisualizationHints {
  /** 0–1 weights per panel. Missing keys default to 0.5. */
  panelEmphasis: Partial<
    Record<"modes" | "gb_window" | "sgwb" | "anomaly" | "lepton" | "formula", number>
  >;
  particleColorMode: ParticleColorMode;
  /** Free-form tags ("torsion_overlay", "wormhole_node", "resonance_inset"). */
  extraOverlays: string[];
  /** \htmlId targets in the formula's annotated LaTeX. */
  formulaTermIds: string[];
}

export interface VisualizationTimelineMeta {
  /** Suggested wall-clock playback duration at 1× speed. */
  durationSeconds: number;
  tauRange: [number, number];
  /** [start_frame_index, end_frame_index] inclusive per phase. */
  phaseBoundaries: Partial<Record<Phase, [number, number]>>;
  visualizationHints: VisualizationHints;
}

export interface VisualizationTimeline {
  runId: string;
  formulaVariant: FormulaVariant;
  /** Typically 200–500 frames. */
  frames: VisualizationFrame[];
  meta: VisualizationTimelineMeta;
}

/* ─────────────────────────────────────────────────────────────────────
 * Service options
 * ────────────────────────────────────────────────────────────────── */

export interface RenderOptions {
  resolution: RenderResolution;
  /** Override the server's default frame budget. */
  framesCount?: number;
}

/* ─────────────────────────────────────────────────────────────────────
 * Pre-baked GPU buffers
 *
 * These are NOT part of the wire schema — they are computed on the
 * frontend after the timeline is fetched and stored as a
 * non-enumerable property on the timeline object. R3F's InstancedMesh
 * reads them in a `useFrame` callback so per-particle data never goes
 * through React.
 * ────────────────────────────────────────────────────────────────── */

export interface BakedTimelineBuffers {
  /** N frames × (3 floats per mode × MAX_MODES). */
  positions: Float32Array[];
  /** N frames × (3 floats per mode × MAX_MODES). RGB, 0–1. */
  colors: Float32Array[];
  /** Active mode count per frame (modes may vary frame-to-frame). */
  modeCount: Uint32Array;
  /** Maximum mode count across the timeline (instance buffer size). */
  maxModes: number;
}

/** Type-guard helper used by panels: timeline post-load enrichment. */
export interface BakedVisualizationTimeline extends VisualizationTimeline {
  /** Always present after `getVisualization` resolves. */
  baked: BakedTimelineBuffers;
}
