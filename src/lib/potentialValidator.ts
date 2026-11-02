/**
 * Coarse linter for the custom potential snippet. Returns decorations
 * describing where the snippet departs from the canonical shape (JAMES
 * DECISION 17): one sympy expression in `phi`, in reduced-Planck units.
 *
 * It is a hint only: it never blocks editing, loading or submitting a config.
 * The backend is the checker that counts (`ucgle_f1.m2_scalar.potentials`:
 * Python `ast` in eval mode, an allow-list of names and calls, size bounds),
 * and it also accepts the legacy `def V(<name>): return <expr>` shape that
 * configs saved from main's Configurator use, so that shape is a warning
 * here, never an error.
 */
export interface PotentialLintIssue {
  line: number; // 1-indexed
  column: number; // 1-indexed
  severity: "info" | "warning" | "error";
  message: string;
}

/** Calls the backend allows (`_SAFE_FUNCTIONS` plus `Rational`). */
const ALLOWED_CALLS = new Set([
  "sqrt",
  "log",
  "exp",
  "sin",
  "cos",
  "tanh",
  "cosh",
  "sinh",
  "Rational",
]);

const CANONICAL = "Write one sympy expression in phi, e.g. `0.5 * m**2 * phi**2`.";

/** `def V(<name>): return <expr>` (one line or two), the legacy shape the API still accepts. */
const LEGACY_DEF = /^\s*def\s+V\s*\(\s*([A-Za-z_]\w*)\s*\)\s*:\s*(?:\n\s*)?return\s+(\S[\s\S]*)$/;

/** Python statement keywords that cannot appear in a single expression. */
const STATEMENT =
  /^\s*(?:import|from|return|for|while|with|class|global|nonlocal|del|pass|raise|try|assert)\b/;

export function lintPotentialSnippet(source: string): PotentialLintIssue[] {
  const issues: PotentialLintIssue[] = [];
  const lines = source.split("\n");
  // Code lines: comments and blank lines dropped (the backend's tokenizer
  // ignores them too), keeping each line's 1-indexed number.
  const code = lines
    .map((text, idx) => ({ text: text.replace(/#.*$/, ""), line: idx + 1 }))
    .filter((l) => l.text.trim() !== "");

  if (code.length === 0) {
    return [{ line: 1, column: 1, severity: "error", message: `Empty snippet. ${CANONICAL}` }];
  }

  const body = code.map((l) => l.text).join("\n");
  const legacy = LEGACY_DEF.exec(body);
  let exprLines = code;
  let symbol = "phi";

  if (legacy) {
    // Accepted by the API, which reads the returned expression with the
    // parameter renamed to phi (Decision 17); flag it, never block it.
    symbol = legacy[1];
    issues.push({
      line: code[0].line,
      column: 1,
      severity: "warning",
      message:
        "Legacy `def V(...): return <expr>` shape: the API accepts it and uses the " +
        `returned expression with \`${symbol}\` read as phi. ${CANONICAL}`,
    });
    const first = code.findIndex((l) => /\breturn\b/.test(l.text));
    exprLines = code
      .slice(first)
      .map((l, i) => (i === 0 ? { ...l, text: l.text.replace(/^.*?\breturn\b/, "") } : l));
  } else if (/^\s*def\b/m.test(body)) {
    const at = code.find((l) => /^\s*def\b/.test(l.text)) ?? code[0];
    issues.push({
      line: at.line,
      column: 1,
      severity: "error",
      message:
        "Only a one-line `def V(<name>): return <expr>` function is accepted; any other " +
        `function body is refused. ${CANONICAL}`,
    });
    return issues;
  }

  for (const { text, line } of exprLines) {
    const stmt = STATEMENT.exec(text);
    if (stmt) {
      issues.push({
        line,
        column: text.search(/\S/) + 1,
        severity: "error",
        message: `Statements are not allowed (\`${stmt[0].trim()}\`). ${CANONICAL}`,
      });
    }
    const assign = /(^|[^=!<>])=(?!=)/.exec(text);
    if (assign) {
      issues.push({
        line,
        column: assign.index + assign[1].length + 1,
        severity: "error",
        message: `Assignments are not allowed; use a parameter name instead. ${CANONICAL}`,
      });
    }
    if (text.includes(";")) {
      issues.push({
        line,
        column: text.indexOf(";") + 1,
        severity: "error",
        message: `\`;\` separates statements. ${CANONICAL}`,
      });
    }
    const caret = text.indexOf("^");
    if (caret >= 0) {
      issues.push({
        line,
        column: caret + 1,
        severity: "error",
        message: "`^` is XOR in Python and is refused; write powers as `**`.",
      });
    }
    for (const call of text.matchAll(/([A-Za-z_][\w.]*)\s*\(/g)) {
      if (!ALLOWED_CALLS.has(call[1])) {
        issues.push({
          line,
          column: (call.index ?? 0) + 1,
          severity: "error",
          message: `\`${call[1]}()\` is not allowed; calls: ${[...ALLOWED_CALLS].join(", ")}.`,
        });
      }
    }
  }

  const usesSymbol = new RegExp(`\\b${symbol}\\b`);
  if (!exprLines.some((l) => usesSymbol.test(l.text))) {
    issues.push({
      line: exprLines[0]?.line ?? 1,
      column: 1,
      severity: "warning",
      message: `The expression does not use \`${symbol}\`; V would be constant.`,
    });
  }

  return issues;
}
