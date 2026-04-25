import { describe, expect, it } from "vitest";
import { RunConfigSchema } from "@/lib/configSchema";
import { kawaiKimDefaults } from "@/lib/configDefaults";

describe("RunConfigSchema", () => {
  it("accepts the V2 Kawai-Kim baseline defaults", () => {
    const parsed = RunConfigSchema.safeParse(kawaiKimDefaults());
    expect(parsed.success).toBe(true);
  });

  it("rejects negative scales (f_a, M1, M_star, S_E2 must be > 0)", () => {
    const cfg = kawaiKimDefaults();
    cfg.couplings.f_a = -1;
    const parsed = RunConfigSchema.safeParse(cfg);
    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      const paths = parsed.error.issues.map((i) => i.path.join("."));
      expect(paths).toContain("couplings.f_a");
    }
  });

  it("rejects non-finite numbers (NaN, Infinity)", () => {
    const cfg = kawaiKimDefaults();
    cfg.couplings.xi = Number.NaN;
    expect(RunConfigSchema.safeParse(cfg).success).toBe(false);

    cfg.couplings.xi = 0.01;
    cfg.reheating.T_reh_GeV = Number.POSITIVE_INFINITY;
    expect(RunConfigSchema.safeParse(cfg).success).toBe(false);
  });

  it("clamps theta_grav to [0, 2π]", () => {
    const cfg = kawaiKimDefaults();
    cfg.couplings.theta_grav = 7;
    expect(RunConfigSchema.safeParse(cfg).success).toBe(false);

    cfg.couplings.theta_grav = -0.1;
    expect(RunConfigSchema.safeParse(cfg).success).toBe(false);

    cfg.couplings.theta_grav = Math.PI;
    expect(RunConfigSchema.safeParse(cfg).success).toBe(true);
  });

  it("requires a recognised potential.kind enum", () => {
    const cfg = kawaiKimDefaults();
    // @ts-expect-error — deliberately bad value
    cfg.potential.kind = "made_up";
    expect(RunConfigSchema.safeParse(cfg).success).toBe(false);
  });

  it("requires a recognised precision tier", () => {
    const cfg = kawaiKimDefaults();
    // @ts-expect-error — deliberately bad value
    cfg.precision = "ultra";
    expect(RunConfigSchema.safeParse(cfg).success).toBe(false);
  });
});
