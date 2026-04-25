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
    // Each labelled term lives inside `\underbrace{value}_{symbol}`. The
    // value can contain nested braces (e.g. `\\times 10^{-3}`), so the
    // assertion just checks that the underbrace label suffix is present
    // for every expected symbol — not the full balanced contents.
    expect(tex).toMatch(/_\{\\xi\}/);
    expect(tex).toMatch(/_\{\\theta_\{\\text\{grav\}\}\}/);
    expect(tex).toMatch(/_\{S_\{E2\}\}/);
    expect(tex).toMatch(/_\{M_1\}/);
    expect(tex).toMatch(/_\{f_a\}/);
    expect(tex).toMatch(/_\{M_\\star\^\{\\,2\}\}/);
    // Six \underbrace calls total (xi, theta_grav, S_E2, M1, f_a, Mstar).
    const underbraceCount = (tex.match(/\\underbrace\{/g) ?? []).length;
    expect(underbraceCount).toBe(6);
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
