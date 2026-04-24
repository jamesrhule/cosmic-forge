import { z } from "zod";
import { fallback } from "@tanstack/zod-adapter";

/**
 * Shared search-param schema for the Visualizer route tree.
 *
 * Declared on the parent (`/visualizer`) and inherited by `$runId`. Every
 * field has a `fallback` so a malformed URL never crashes the route — it
 * just snaps back to the default. The store is the source of truth for
 * transport state at runtime; the URL is the source of truth on first
 * load and on hard refresh.
 */
export const visualizerSearchSchema = z.object({
  /** Optional partner run id for A↔B comparison. */
  runB: fallback(z.string().min(1).optional(), undefined).optional(),
  /** Comparison mode mirrors the store. */
  mode: fallback(
    z.enum(["single", "ab_overlay", "split_screen"]),
    "single",
  ).default("single"),
  /** Sync-by-phase toggle (P hotkey). */
  phase: fallback(z.boolean(), false).default(false),
  /** Initial scrubber frame; clamped to the timeline length at mount. */
  frame: fallback(z.number().int().min(0), 0).default(0),
});

export type VisualizerSearch = z.infer<typeof visualizerSearchSchema>;
