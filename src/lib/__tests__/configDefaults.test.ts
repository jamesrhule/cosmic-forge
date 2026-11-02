import { describe, expect, it } from "vitest";
import { defaultsForPotential, kawaiKimDefaults } from "@/lib/configDefaults";
import { samplePotential } from "@/lib/potentialEvaluator";

// W1-PARAMS: the Configurator's defaults live in configDefaults.json, which the
// backend test test_frontend_potential_configs.py checks against the API.
describe("Configurator defaults", () => {
  it("makes the V2 natural default the paper benchmark in Configurator units (Decision 15)", () => {
    expect(kawaiKimDefaults().potential).toEqual({
      kind: "natural",
      params: { f: 2.118624e19, Lambda4: 2.563334027300118e-9 },
    });
    expect(Object.keys(kawaiKimDefaults().potential.params)).toEqual(["f", "Lambda4"]);
    // f = 8.7 M_Pl (M_PL_GEV = 2.4352e18, backend m1_background) and
    // Λ = 0.0071154324599829784 M_Pl, the Decision 11 benchmark.
    const { f, Lambda4 } = kawaiKimDefaults().potential.params;
    expect(f / 2.4352e18).toBe(8.7);
    expect(Math.abs(Lambda4 ** 0.25 / 0.0071154324599829784 - 1)).toBeLessThan(1e-15);
  });

  it("gives hilltop an explicit V0 alongside mu and p", () => {
    expect(defaultsForPotential("hilltop")).toEqual({ V0: 1e-7, mu: 1e16, p: 4 });
  });

  it("returns fresh objects, so editing the form never changes the defaults", () => {
    const a = defaultsForPotential("natural");
    a.f = 1;
    expect(defaultsForPotential("natural").f).toBe(2.118624e19);
    const v2 = kawaiKimDefaults();
    v2.couplings.xi = 1;
    v2.potential.params.Lambda4 = 1;
    expect(kawaiKimDefaults().couplings.xi).toBe(0.0085);
    expect(kawaiKimDefaults().potential.params.Lambda4).toBe(2.563334027300118e-9);
  });

  it("previews hilltop with the configured V0 (the old fixed 1e-7 is the default)", () => {
    const withDefault = samplePotential("hilltop", defaultsForPotential("hilltop"))!;
    const withoutV0 = samplePotential("hilltop", { mu: 1e16, p: 4 })!;
    expect(withDefault).toEqual(withoutV0);
    const doubled = samplePotential("hilltop", { ...defaultsForPotential("hilltop"), V0: 2e-7 })!;
    expect(doubled[10].V).toBe(2 * withDefault[10].V);
  });

  it("previews a parameter the form lacks with the Configurator default (one source)", () => {
    const withDefaults = samplePotential("natural", defaultsForPotential("natural"))!;
    expect(samplePotential("natural", {})).toEqual(withDefaults);
    expect(samplePotential("starobinsky", {})).toEqual(
      samplePotential("starobinsky", defaultsForPotential("starobinsky")),
    );
  });
});
