import { describe, expect, it } from "vitest";
import { DEFAULT_CUSTOM_PYTHON } from "@/lib/configDefaults";
import { lintPotentialSnippet } from "@/lib/potentialValidator";

// JAMES DECISION 17: the canonical custom snippet is one sympy expression in
// phi; `def V(<name>): return <expr>` stays accepted by the API, so the linter
// may warn about it but never errors on it.
const errors = (src: string) => lintPotentialSnippet(src).filter((i) => i.severity === "error");

// main's Configurator default, saved in configs before Decision 17.
const MAIN_DEFAULT = `# Custom inflaton potential V(psi).
# Must define a function V(psi) returning a float in Planck units.
# Pure Python (no imports). The backend AST-checks this snippet.
def V(psi):
    M = 1.3e-5
    return 0.75 * M**2 * (1.0 - 2.718281828 ** (-0.8164965809 * psi)) ** 2
`;

describe("custom potential linter (Decision 17)", () => {
  it("the Configurator's default is the canonical expression form and lints clean", () => {
    expect(DEFAULT_CUSTOM_PYTHON).not.toMatch(/\bdef\b|\breturn\b/);
    expect(DEFAULT_CUSTOM_PYTHON).toMatch(/\bphi\b/);
    expect(lintPotentialSnippet(DEFAULT_CUSTOM_PYTHON)).toEqual([]);
  });

  it("the default computes the potential main's def V(psi) default did", () => {
    const expr = DEFAULT_CUSTOM_PYTHON.split("\n")
      .filter((l) => l.trim() !== "" && !l.trim().startsWith("#"))
      .join("\n");
    // Evaluate both sides as JS arithmetic (`**` is the same operator) at a
    // few points; the browser never runs user snippets, this is a test only.
    const asJs = (src: string, name: string) =>
      new Function(name, `return ${src.trim()};`) as (x: number) => number;
    const canonical = asJs(expr, "phi");
    const main = (psi: number) => {
      const M = 1.3e-5;
      return 0.75 * M ** 2 * (1.0 - 2.718281828 ** (-0.8164965809 * psi)) ** 2;
    };
    for (const x of [-1, 0, 0.5, 2, 4]) expect(canonical(x)).toBe(main(x));
  });

  it("warns on, but never errors on, the legacy single-return def V(<name>) shape", () => {
    for (const src of [
      "def V(psi): return 0.5 * psi**2",
      "def V(x):\n    return 1e-10 * (1 - cos(x / 8.7))",
    ]) {
      const issues = lintPotentialSnippet(src);
      expect(errors(src)).toEqual([]);
      expect(issues.some((i) => i.severity === "warning" && /Legacy/.test(i.message))).toBe(true);
    }
  });

  it("errors on any other function body, such as main's two-statement default", () => {
    const e = errors(MAIN_DEFAULT);
    expect(e).toHaveLength(1);
    expect(e[0]).toMatchObject({ line: 4, message: expect.stringMatching(/one sympy expression/) });
  });

  it("flags what the backend refuses: statements, assignments, ^, disallowed calls", () => {
    expect(errors("import os\nphi")[0].message).toMatch(/Statements are not allowed/);
    expect(errors("m = 2\nm * phi")[0].message).toMatch(/Assignments are not allowed/);
    expect(errors("phi ^ 2")[0]).toMatchObject({
      column: 5,
      message: expect.stringMatching(/\*\*/),
    });
    expect(errors("open(phi)")[0].message).toMatch(/`open\(\)` is not allowed/);
    expect(errors("phi; phi")[0].message).toMatch(/separates statements/);
    expect(errors("exp(-phi) + Rational(1, 2) * sqrt(phi**2)")).toEqual([]);
  });

  it("warns when the expression does not depend on phi", () => {
    const issues = lintPotentialSnippet("1e-10");
    expect(errors("1e-10")).toEqual([]);
    expect(issues[0]).toMatchObject({ severity: "warning", message: expect.stringMatching(/phi/) });
  });
});
