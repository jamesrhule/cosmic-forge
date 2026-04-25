import { describe, expect, it } from "vitest";
import { checkConfigValidity } from "@/lib/validity";
import { kawaiKimDefaults } from "@/lib/configDefaults";

describe("checkConfigValidity", () => {
  it("returns level 'ok' for the Kawai-Kim baseline", () => {
    const result = checkConfigValidity(kawaiKimDefaults());
    expect(result.level).toBe("ok");
    expect(result.details).toEqual([]);
  });

  it("flags ξ ≤ 0 as a hard error", () => {
    const cfg = kawaiKimDefaults();
    cfg.couplings.xi = 0;
    const result = checkConfigValidity(cfg);
    expect(result.level).toBe("error");
    expect(result.details.some((d) => d.field === "xi" && d.level === "error")).toBe(true);
  });

  it("warns on unusually large ξ (> 1) without erroring", () => {
    const cfg = kawaiKimDefaults();
    cfg.couplings.xi = 5;
    const result = checkConfigValidity(cfg);
    expect(result.level).toBe("warn");
    expect(result.details[0]).toMatchObject({ field: "xi", level: "warn" });
  });

  it("flags θ_grav outside [0, 2π] as a hard error", () => {
    const cfg = kawaiKimDefaults();
    cfg.couplings.theta_grav = -1;
    expect(checkConfigValidity(cfg).level).toBe("error");
    cfg.couplings.theta_grav = 10;
    expect(checkConfigValidity(cfg).level).toBe("error");
  });

  it("error wins over warn when both apply (highest severity propagates)", () => {
    const cfg = kawaiKimDefaults();
    cfg.couplings.xi = 5; // warn
    cfg.reheating.T_reh_GeV = -1; // error
    const result = checkConfigValidity(cfg);
    expect(result.level).toBe("error");
    expect(result.message).toMatch(/hard constraint/i);
  });

  it("warns when M1 is outside the natural seesaw window", () => {
    const cfg = kawaiKimDefaults();
    cfg.couplings.M1 = 1; // way too small
    const result = checkConfigValidity(cfg);
    expect(result.level).toBe("warn");
    expect(result.details.some((d) => d.field === "M1")).toBe(true);
  });
});
