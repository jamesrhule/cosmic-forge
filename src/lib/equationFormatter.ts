import type { RunConfig } from "@/types/domain";

/** Format a number as a LaTeX scientific-notation literal. */
function sciTex(v: number, sig = 3): string {
  if (!Number.isFinite(v)) return String(v);
  if (v === 0) return "0";
  const exp = Math.floor(Math.log10(Math.abs(v)));
  const mantissa = v / 10 ** exp;
  const m = mantissa.toFixed(sig - 1);
  if (exp === 0) return m;
  return `${m}\\times 10^{${exp}}`;
}

/**
 * Render a scientific-notation literal raised to an integer power. Wraps
 * the literal in parentheses so KaTeX never sees an adjacent double
 * superscript like `10^{18}^2`.
 */
function sciTexPow(v: number, exp: number, sig = 3): string {
  return `\\left(${sciTex(v, sig)}\\right)^{${exp}}`;
}

/**
 * Render the F1 boxed equation with substituted numeric values from
 * the current `RunConfig`.
 */
export function renderF1WithValues(config: RunConfig): string {
  const c = config.couplings;
  return [
    "\\boxed{\\,\\eta_B \\;=\\; \\mathcal{N}\\,",
    `\\underbrace{${sciTex(c.xi)}}_{\\xi}\\,`,
    `\\underbrace{${sciTex(c.theta_grav)}}_{\\theta_{\\text{grav}}}\\;`,
    "\\langle R\\widetilde{R}\\rangle_\\Psi\\;",
    `\\frac{\\underbrace{${sciTex(c.S_E2)}}_{S_{E2}}\\,`,
    `\\underbrace{${sciTex(c.M1)}}_{M_1}}{`,
    `\\underbrace{${sciTex(c.f_a)}}_{f_a}\\,`,
    `\\underbrace{${sciTexPow(c.M_star, 2)}}_{M_\\star^{\\,2}}}\\,}`,
  ].join("");
}
