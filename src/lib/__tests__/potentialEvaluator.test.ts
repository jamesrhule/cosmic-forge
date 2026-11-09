import { describe, expect, it } from "vitest";
import { defaultsForPotential, M_PL_GEV } from "@/lib/configDefaults";
import { samplePotential } from "@/lib/potentialEvaluator";
import type { PotentialKind } from "@/types/domain";
import m2 from "./fixtures/potential-preview.m2.json";

// Gate 1 round 4 (R4-FEOPS): the Configurator's V(ψ) preview draws the
// potential the run uses. The vectors are M2's own V(ψ)
// (scripts/gen_potential_vectors.py; backend/tests/test_potential_vectors.py
// keeps them equal to what M2 computes).
describe("V(ψ) preview against M2", () => {
  it("samples the grid the vectors were computed on", () => {
    const got = samplePotential("starobinsky", defaultsForPotential("starobinsky"))!;
    expect(got.map((s) => s.psi)).toEqual(m2.psi);
  });

  for (const c of m2.cases) {
    it(`matches M2 for ${c.kind} ${JSON.stringify(c.params)}`, () => {
      const got = samplePotential(
        c.kind as PotentialKind,
        c.params as unknown as Record<string, number>,
      )!;
      const scale = Math.max(...c.V.map(Math.abs));
      got.forEach((s, i) => {
        // 1 − cos near its zero loses digits on either side; the rest is
        // the same float arithmetic as numpy's.
        expect(Math.abs(s.V - c.V[i])).toBeLessThanOrEqual(1e-9 * Math.abs(c.V[i]) + 1e-15 * scale);
      });
    });
  }

  it("covers each built-in kind's Configurator default", () => {
    for (const kind of ["starobinsky", "natural", "hilltop"] as const) {
      expect(m2.cases).toContainEqual(
        expect.objectContaining({ kind, params: defaultsForPotential(kind) }),
      );
    }
  });

  it("draws Decision 15's natural default as a curve, not a flat line", () => {
    const V = samplePotential("natural", defaultsForPotential("natural"))!.map((s) => s.V);
    const span = (Math.max(...V) - Math.min(...V)) / Math.max(...V);
    // 1 − cos(ψ/8.7) on [-2, 4]: from 0 at ψ = 0 up to its value at ψ = 4.
    expect(span).toBeGreaterThan(0.99);
    expect(Math.min(...V)).toBeGreaterThanOrEqual(0);
  });

  it("converts GeV with the engine's M_Pl (configDefaults.json units)", () => {
    expect(defaultsForPotential("natural").f / M_PL_GEV).toBe(8.7);
  });
});
