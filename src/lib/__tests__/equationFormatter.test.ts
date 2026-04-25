import { describe, expect, it } from "vitest";
import { renderF1WithValues } from "@/lib/equationFormatter";
import { kawaiKimDefaults } from "@/lib/configDefaults";

describe("renderF1WithValues", () => {
  it("emits a balanced \\boxed{...} envelope for the baseline", () => {
    const tex = renderF1WithValues(kawaiKimDefaults());
    expect(tex.startsWith("\\boxed{")).toBe(true);
    // KaTeX requires brace balance — count opens vs. closes.
    const opens = (tex.match(/\{/g) ?? []).length;
    const closes = (tex.match(/\}/g) ?? []).length;
    expect(opens).toBe(closes);
  });

  it("includes underbraced labels for every coupling", () => {
    const tex = renderF1WithValues(kawaiKimDefaults());
    // Each labelled term lives inside `\underbrace{value}_{symbol}`.
    expect(tex).toMatch(/\\underbrace\{[^}]+\}_\{\\xi\}/);
    expect(tex).toMatch(/\\underbrace\{[^}]+\}_\{\\theta_\{\\text\{grav\}\}\}/);
    expect(tex).toMatch(/\\underbrace\{[^}]+\}_\{S_\{E2\}\}/);
    expect(tex).toMatch(/\\underbrace\{[^}]+\}_\{M_1\}/);
    expect(tex).toMatch(/\\underbrace\{[^}]+\}_\{f_a\}/);
    expect(tex).toMatch(/\\underbrace\{[^}]+\}_\{M_\\star\^\{\\,2\}\}/);
  });

  it("wraps a value raised to a power in parentheses (no `10^{18}^2`)", () => {
    const tex = renderF1WithValues(kawaiKimDefaults());
    // The Mstar term is squared — KaTeX would error on adjacent
    // double superscripts. Guard with explicit \left(...\right).
    expect(tex).toMatch(/\\left\([^)]+\\right\)\^\{2\}/);
    expect(tex).not.toMatch(/\}\^\{[0-9]+\}\^\{[0-9]+\}/);
  });

  it("renders numeric mantissa × 10^exp scientific form for large magnitudes", () => {
    const tex = renderF1WithValues(kawaiKimDefaults());
    // f_a defaults to 1e16, M_star to 2.4e18 — both must hit the
    // exponential branch.
    expect(tex).toMatch(/\\times\s*10\^\{16\}/);
    expect(tex).toMatch(/\\times\s*10\^\{18\}/);
  });
});
