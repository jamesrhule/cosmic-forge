/**
 * Wrap each term in the latex with `\htmlId{vfx-<term>}{<term>}`.
 *
 * Strategy: do a longest-first textual substitution on the raw LaTeX.
 * Terms in F1-F7 are short and unique enough (e.g. `xi`, `theta_grav`,
 * `RtildeR`, `S_E2`) that we can rely on simple word boundaries built
 * out of the surrounding LaTeX punctuation. Anything not found is
 * silently skipped — the formula still renders.
 *
 * Only the first occurrence of each fragment is wrapped (`String.replace`
 * with a literal). That matches the panel-formula contract where the
 * `\htmlId` glow target is unique per term.
 */

// Map short IDs to LaTeX fragments we expect to see verbatim.
export const TERM_TO_LATEX: Record<string, string> = {
  xi: "\\xi",
  theta_grav: "\\theta_{\\text{grav}}",
  RtildeR: "\\langle R\\widetilde{R}\\rangle_\\Psi",
  S_E2: "S_{\\!E2}",
  M1: "M_1",
  fa: "f_a",
  Mstar: "M_\\star^2",
  Treh: "T_{\\text{reh}}",
  Gamma_phi: "\\Gamma_\\phi",
  dGamma: "\\delta\\Gamma_\\phi",
  lambdaHPsi: "\\lambda_{H\\Psi}",
};

export function annotateLatex(latex: string, termIds: readonly string[]): string {
  // Sort by descending fragment length so we substitute the most specific
  // tokens first (`M_\star^2` before `M_1`).
  const ordered = [...termIds].sort(
    (a, b) => (TERM_TO_LATEX[b]?.length ?? 0) - (TERM_TO_LATEX[a]?.length ?? 0),
  );

  let out = latex;
  for (const term of ordered) {
    const frag = TERM_TO_LATEX[term];
    if (!frag) continue;
    if (!out.includes(frag)) continue;
    // \htmlId requires KaTeX trust mode in normal use, but our InlineMath
    // wrapper passes through; the rendered DOM will carry id="vfx-<term>".
    const wrapped = `\\htmlId{vfx-${term}}{${frag}}`;
    out = out.replace(frag, wrapped);
  }
  return out;
}
