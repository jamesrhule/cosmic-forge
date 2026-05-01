/**
 * Cosmology / UCGLE-F1 DomainPlugin (PROMPT 4 v2).
 *
 * The cosmology shell predates the QCompass multi-domain layer by
 * several PROMPTs. This file is a thin metadata wrapper around
 * the existing routes / fixtures so the multi-domain registry can
 * reference cosmology uniformly. No runtime behaviour changes
 * for the cosmology view — `enabled()` returns `true` in every
 * flag configuration.
 */

import type { DomainPlugin } from "./types";

export const cosmologyUcglef1: DomainPlugin = {
  id: "cosmology",
  label: "Cosmology · UCGLE-F1",
  shortLabel: "Cosmology",
  route: "/",
  manifestSchemaPath: "/api/qcompass/domains/cosmology/schema",
  manifestSchemaFixture: "runs/kawai-kim-natural.json",
  fixturesRoot: "/fixtures/runs",
  auditCheckIds: [
    "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8",
    "S9", "S10", "S11", "S12", "S13", "S14", "S15",
  ] as const,
  references: ["1702.07689", "2007.08029", "2412.09490", "2403.09373"] as const,
  enabled: () => true,
};
