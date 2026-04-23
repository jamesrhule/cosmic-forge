/**
 * Stub linter for the custom Python potential snippet. Returns coarse
 * decorations describing where the snippet violates a tiny safelist.
 *
 * Claude Code replaces this with the real physics checker (AST whitelist,
 * differentiability check, dimensional analysis) once the backend lands.
 */
export interface PotentialLintIssue {
  line: number; // 1-indexed
  column: number; // 1-indexed
  severity: "info" | "warning" | "error";
  message: string;
}

const FORBIDDEN_PATTERNS: Array<{ pattern: RegExp; message: string }> = [
  { pattern: /\bimport\s+os\b/, message: "Module 'os' is not allowed." },
  {
    pattern: /\bimport\s+subprocess\b/,
    message: "Module 'subprocess' is not allowed.",
  },
  { pattern: /\bopen\s*\(/, message: "File I/O is not allowed." },
  { pattern: /\beval\s*\(/, message: "eval() is not allowed." },
  { pattern: /\bexec\s*\(/, message: "exec() is not allowed." },
];

export function lintPotentialSnippet(source: string): PotentialLintIssue[] {
  const issues: PotentialLintIssue[] = [];
  const lines = source.split("\n");
  lines.forEach((text, idx) => {
    for (const { pattern, message } of FORBIDDEN_PATTERNS) {
      const match = text.match(pattern);
      if (match && match.index !== undefined) {
        issues.push({
          line: idx + 1,
          column: match.index + 1,
          severity: "error",
          message,
        });
      }
    }
    if (/print\s*\(/.test(text)) {
      issues.push({
        line: idx + 1,
        column: text.indexOf("print") + 1,
        severity: "warning",
        message: "print() output is ignored at runtime.",
      });
    }
  });

  if (!/def\s+V\s*\(/.test(source)) {
    issues.push({
      line: 1,
      column: 1,
      severity: "error",
      message: "Snippet must define a function `V(psi)`.",
    });
  }

  return issues;
}
