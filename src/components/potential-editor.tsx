import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorView, Decoration } from "@codemirror/view";
import { StateField, StateEffect, RangeSetBuilder } from "@codemirror/state";
import { useMemo } from "react";
import { useTheme } from "@/store/ui";
import {
  lintPotentialSnippet,
  type PotentialLintIssue,
} from "@/lib/potentialValidator";

export interface PotentialEditorProps {
  value: string;
  onChange: (next: string) => void;
}

/**
 * CodeMirror 6 Python editor with read-only lint decorations driven by
 * `lintPotentialSnippet`. The browser NEVER executes the snippet — the
 * backend re-validates with a real AST checker.
 */
export function PotentialEditor({ value, onChange }: PotentialEditorProps) {
  const theme = useTheme((s) => s.theme);
  const issues = useMemo(() => lintPotentialSnippet(value), [value]);

  const lintField = useMemo(
    () =>
      StateField.define({
        create: () => buildDecorations(value, issues),
        update(deco, tr) {
          for (const e of tr.effects) {
            if (e.is(setIssuesEffect)) {
              return buildDecorations(tr.newDoc.toString(), e.value);
            }
          }
          if (tr.docChanged) return deco.map(tr.changes);
          return deco;
        },
        provide: (f) => EditorView.decorations.from(f),
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  return (
    <div className="overflow-hidden rounded-md border">
      <CodeMirror
        value={value}
        height="240px"
        theme={theme === "dark" ? oneDark : undefined}
        extensions={[python(), lintField, lintTheme]}
        onChange={(next, viewUpdate) => {
          onChange(next);
          const nextIssues = lintPotentialSnippet(next);
          viewUpdate.view.dispatch({ effects: setIssuesEffect.of(nextIssues) });
        }}
        basicSetup={{
          lineNumbers: true,
          highlightActiveLine: true,
          foldGutter: false,
        }}
      />
      {issues.length > 0 && (
        <ul className="border-t bg-muted/40 px-3 py-2 text-xs">
          {issues.map((iss, i) => (
            <li
              key={i}
              className="font-mono"
              style={{
                color:
                  iss.severity === "error"
                    ? "var(--color-destructive)"
                    : iss.severity === "warning"
                      ? "var(--color-status-canceled)"
                      : "var(--color-muted-foreground)",
              }}
            >
              [{iss.severity}] line {iss.line}: {iss.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const setIssuesEffect = StateEffect.define<PotentialLintIssue[]>();

function buildDecorations(doc: string, issues: PotentialLintIssue[]) {
  const lines = doc.split("\n");
  const builder = new RangeSetBuilder<Decoration>();
  // Decorations must be added in document order.
  const sorted = [...issues].sort((a, b) => a.line - b.line);
  let cursor = 0;
  for (let i = 0; i < lines.length; i++) {
    const lineNum = i + 1;
    const lineStart = cursor;
    const matching = sorted.filter((iss) => iss.line === lineNum);
    if (matching.length > 0) {
      const sev = matching.some((m) => m.severity === "error")
        ? "error"
        : matching.some((m) => m.severity === "warning")
          ? "warning"
          : "info";
      builder.add(
        lineStart,
        lineStart,
        Decoration.line({ class: `cm-lint-line cm-lint-${sev}` }),
      );
    }
    cursor += lines[i].length + 1;
  }
  return builder.finish();
}

const lintTheme = EditorView.baseTheme({
  ".cm-lint-line.cm-lint-error": {
    backgroundColor: "color-mix(in oklab, var(--color-destructive) 12%, transparent)",
  },
  ".cm-lint-line.cm-lint-warning": {
    backgroundColor: "color-mix(in oklab, var(--color-status-canceled) 12%, transparent)",
  },
  ".cm-lint-line.cm-lint-info": {
    backgroundColor: "color-mix(in oklab, var(--color-accent-indigo) 8%, transparent)",
  },
});
