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
 *
 * The shape rules follow the backend parser: a snippet the backend refuses
 * for its shape gets an error here, and one it accepts gets none. The
 * vitest checks this on backend-generated vectors
 * (`src/lib/__tests__/fixtures/potential-snippets.backend.json`, written by
 * `scripts/gen_potential_vectors.py` and kept current by
 * `backend/tests/test_potential_vectors.py`). The backend's size and
 * magnitude bounds stay backend-only.
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

/**
 * `def V(<name>): return <expr>`, the legacy shape the API still accepts:
 * one positional parameter and a body of one `return`, which a docstring
 * may precede (backend `_function_return`).
 */
const LEGACY_DEF =
  /^\s*def\s+V\s*\(\s*([A-Za-z_]\w*)\s*\)\s*:\s*(?:\n\s*)?(?:(?:"""[\s\S]*?"""|'''[\s\S]*?'''|"[^"\n]*"|'[^'\n]*')\s*\n\s*)?return\s+(\S[\s\S]*)$/;

/** The line of a legacy def that holds its `return`. */
const RETURN_LINE = /^\s*return\b|^\s*def\b.*:\s*return\b/;

/** Python statement keywords that cannot appear in a single expression. */
const STATEMENT =
  /^\s*(?:import|from|return|for|while|with|class|global|nonlocal|del|pass|raise|try|assert)\b/;

/** Expression keywords the backend's allow-list refuses (Lambda, IfExp, BoolOp, Not, Compare). */
const KEYWORD = /\b(lambda|if|else|and|or|not|in|is|yield|await)\b/g;

/** Comparisons (`Compare` is refused); `<<` and `>>` are shifts, see OPERATOR. */
const COMPARISON = /==|!=|<=|>=|(?<![<>])[<>](?![<>=])/g;

/** Operators outside `+ - * / **` (`^` has its own message). */
const OPERATOR = /\/\/|<<|>>|[%@&|~]/g;

/** An attribute that is not called (a called one is a disallowed call). */
const ATTRIBUTE = /\b[A-Za-z_]\w*\s*\.\s*[A-Za-z_]\w*\b(?!\s*\()/g;

/** An allowed function's name used without a call (`'exp' must be called`). */
const UNCALLED = /\b(sqrt|log|exp|sin|cos|tanh|cosh|sinh|Rational)\b(?!\s*\()/g;

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
    const first = code.findIndex((l) => RETURN_LINE.test(l.text));
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
        "Only a `def V(<name>)` whose body is one `return <expr>` (a docstring may precede " +
        `it) is accepted; any other function is refused. ${CANONICAL}`,
    });
    return issues;
  }

  // Bracket depth across lines: a line break outside brackets (and without a
  // trailing backslash) ends the expression, so a next line is a second
  // statement, which the backend refuses.
  let depth = 0;
  for (const [idx, { text, line }] of exprLines.entries()) {
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
    const rules: Array<[RegExp, (m: RegExpMatchArray) => string]> = [
      [KEYWORD, (m) => `\`${m[0]}\` is not allowed in a potential. ${CANONICAL}`],
      [COMPARISON, (m) => `Comparisons (\`${m[0]}\`) are not allowed. ${CANONICAL}`],
      [OPERATOR, (m) => `\`${m[0]}\` is not allowed; operators: + - * / **.`],
      [/[[\]{}]/g, () => `Lists, dicts, sets and indexing are not allowed. ${CANONICAL}`],
      [/["']/g, () => `String literals are not allowed. ${CANONICAL}`],
      [ATTRIBUTE, (m) => `Attributes (\`${m[0]}\`) are not allowed. ${CANONICAL}`],
      [UNCALLED, (m) => `\`${m[0]}\` must be called, e.g. \`${m[0]}(phi)\`.`],
    ];
    for (const [rule, message] of rules) {
      const m = [...text.matchAll(rule)][0];
      if (m) {
        issues.push({ line, column: (m.index ?? 0) + 1, severity: "error", message: message(m) });
      }
    }

    for (const ch of text) {
      if ("([{".includes(ch)) depth += 1;
      else if (")]}".includes(ch)) depth -= 1;
    }
    const next = exprLines[idx + 1];
    if (next && depth <= 0 && !text.trimEnd().endsWith("\\")) {
      issues.push({
        line: next.line,
        column: next.text.search(/\S/) + 1,
        severity: "error",
        message:
          "A new line outside parentheses starts a second statement; the snippet is one " +
          `expression (wrap a multi-line one in parentheses). ${CANONICAL}`,
      });
    }
  }
  if (depth !== 0) {
    const last = exprLines[exprLines.length - 1];
    issues.push({
      line: last.line,
      column: 1,
      severity: "error",
      message: `Unbalanced parentheses. ${CANONICAL}`,
    });
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
