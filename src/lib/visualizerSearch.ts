import { z } from "zod";

/**
 * Shared search-param schema for the Visualizer route tree.
 *
 * Declared on the parent (`/visualizer`) and inherited by `$runId`. Every
 * field has a `.catch()` fallback so a malformed URL never crashes the
 * route — it just snaps back to the default. The schema is a zod 4
 * Standard Schema, passed directly to `validateSearch`. The store is the source of truth for
 * transport state at runtime; the URL is the source of truth on first
 * load and on hard refresh.
 */
export const visualizerSearchSchema = z.object({
  /** Optional partner run id for A↔B comparison. */
  runB: z.string().min(1).optional().catch(undefined),
  /** Comparison mode mirrors the store. */
  mode: z.enum(["single", "ab_overlay", "split_screen"]).default("single").catch("single"),
  /** Sync-by-phase toggle (P hotkey). */
  phase: z.boolean().default(false).catch(false),
  /** Initial scrubber frame; clamped to the timeline length at mount. */
  frame: z.number().int().min(0).default(0).catch(0),
});

export type VisualizerSearch = z.infer<typeof visualizerSearchSchema>;
