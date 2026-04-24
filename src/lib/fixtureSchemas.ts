/**
 * Minimal runtime shape validators for bundled fixtures.
 *
 * These are intentionally **lenient** — we only assert the fields that
 * downstream code dereferences, leaving room for the canonical Pydantic
 * models to grow without breaking the fixtures-first dev loop.
 *
 * Anything that fails one of these schemas should be treated as a build
 * accident (truncated file, hand-edit gone wrong) and surfaced as
 * "Couldn't load <surface>" rather than a deep render crash.
 */
import { z } from "zod";

const finiteNumber = z.number().refine(Number.isFinite, "must be a finite number");

/* ───────── benchmarks.json ───────── */

const RunConfigShape = z.object({
  potential: z.object({
    kind: z.string(),
    params: z.record(z.string(), z.number()),
    customPython: z.string().optional(),
  }),
  couplings: z.object({
    xi: finiteNumber,
    theta_grav: finiteNumber,
    f_a: finiteNumber,
    M_star: finiteNumber,
    M1: finiteNumber,
    S_E2: finiteNumber,
  }),
  reheating: z.object({
    Gamma_phi: finiteNumber,
    T_reh_GeV: finiteNumber,
  }),
  precision: z.string(),
});

export const BenchmarkIndexShape = z.object({
  benchmarks: z
    .array(
      z.object({
        id: z.string().min(1),
        label: z.string(),
        arxivId: z.string(),
        description: z.string(),
        config: RunConfigShape,
        expectedEta_B: finiteNumber,
      }),
    )
    .min(1, "benchmarks list is empty"),
});

/* ───────── runs/*.json ───────── */

const AuditCheckShape = z.object({
  id: z.string().min(1),
  name: z.string(),
  verdict: z.string(),
  references: z.array(z.string()),
  notes: z.string(),
});

const AuditReportShape = z.object({
  checks: z.array(AuditCheckShape),
  summary: z.object({
    passed: z.number().int(),
    total: z.number().int(),
    blocking: z.boolean(),
  }),
});

export const RunResultShape = z
  .object({
    id: z.string().min(1),
    status: z.string(),
    audit: AuditReportShape,
    eta_B: z.object({
      value: finiteNumber,
      uncertainty: finiteNumber,
    }),
  })
  // Allow the rest of RunResult through untouched — we don't want to
  // re-encode the whole domain here.
  .passthrough();

/* ───────── models.json ───────── */

export const ModelDescriptorListShape = z
  .array(
    z.object({
      id: z.string().min(1),
      displayName: z.string(),
      provider: z.enum(["local", "remote"]),
      format: z.string(),
      contextWindow: z.number().int().positive(),
      license: z.string(),
      source: z.string(),
      recommended: z.boolean(),
      tags: z.array(z.string()),
    }),
  )
  .min(1, "models list is empty");

/* ───────── formulas/F1-F7.json ───────── */

export const FormulaListShape = z
  .array(
    z.object({
      id: z.string().min(1),
      name: z.string(),
      latex: z.string().min(1),
      notes: z.string().optional(),
    }),
  )
  .min(1, "formula list is empty");

/* ───────── scans/*.json ───────── */

export const ScanResultShape = z
  .object({
    id: z.string().min(1),
    xAxis: z.object({
      field: z.string(),
      values: z.array(finiteNumber).min(1),
      log: z.boolean(),
    }),
    yAxis: z.object({
      field: z.string(),
      values: z.array(finiteNumber).min(1),
      log: z.boolean(),
    }),
    eta_B_grid: z.array(z.array(finiteNumber).min(1)).min(1),
  })
  .superRefine((scan, ctx) => {
    const ny = scan.yAxis.values.length;
    const nx = scan.xAxis.values.length;
    if (scan.eta_B_grid.length !== ny) {
      ctx.addIssue({
        code: "custom",
        path: ["eta_B_grid"],
        message: `expected ${ny} rows (yAxis length), got ${scan.eta_B_grid.length}`,
      });
    }
    for (let i = 0; i < scan.eta_B_grid.length; i++) {
      const row = scan.eta_B_grid[i];
      if (row.length !== nx) {
        ctx.addIssue({
          code: "custom",
          path: ["eta_B_grid", i],
          message: `expected ${nx} cols (xAxis length), got ${row.length}`,
        });
        break;
      }
    }
  });

/* ───────── visualizations/*.json ─────────
 *
 * Lenient: only the fields that downstream code dereferences before any
 * UI surface can render a single frame. Anything else passes through so
 * the canonical Pydantic model can grow without breaking fixtures.
 */

const LeptonFlowShape = z.object({
  chiral_gw: finiteNumber,
  anomaly: finiteNumber,
  delta_N_L: finiteNumber,
  eta_B_running: finiteNumber,
});

const VisualizationFrameShape = z
  .object({
    tau: finiteNumber,
    phase: z.string().min(1),
    B_plus: finiteNumber,
    B_minus: finiteNumber,
    xi_dot_H: finiteNumber,
    lepton_flow: LeptonFlowShape,
    active_terms: z.array(z.string()),
    modes: z.array(z.unknown()),
  })
  .passthrough();

const VisualizationHintsShape = z
  .object({
    panelEmphasis: z.record(z.string(), z.number()),
    particleColorMode: z.enum(["chirality", "kk_level", "condensate", "resonance"]),
    extraOverlays: z.array(z.string()),
    formulaTermIds: z.array(z.string()),
  })
  .passthrough();

const VisualizationTimelineMetaShape = z
  .object({
    durationSeconds: finiteNumber,
    tauRange: z.tuple([finiteNumber, finiteNumber]),
    phaseBoundaries: z.record(z.string(), z.tuple([z.number().int(), z.number().int()])),
    visualizationHints: VisualizationHintsShape,
  })
  .passthrough();

export const VisualizationTimelineShape = z
  .object({
    runId: z.string().min(1),
    formulaVariant: z.enum(["F1", "F2", "F3", "F4", "F5", "F6", "F7"]),
    frames: z.array(VisualizationFrameShape).min(1, "timeline has no frames"),
    meta: VisualizationTimelineMetaShape,
  })
  .passthrough();
