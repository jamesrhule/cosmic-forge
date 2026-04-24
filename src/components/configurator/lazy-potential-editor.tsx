import { lazy, Suspense } from "react";
import type { PotentialEditorProps } from "@/components/potential-editor";

/**
 * Lazy wrapper for the CodeMirror-backed Python editor. Pulls
 * `@uiw/react-codemirror`, `@codemirror/lang-python`, and the One Dark
 * theme out of the main bundle — they only load when the user picks
 * the "Custom (Python)" potential kind.
 */
const PotentialEditorInner = lazy(() =>
  import("@/components/potential-editor").then((mod) => ({
    default: mod.PotentialEditor,
  })),
);

export function LazyPotentialEditor(props: PotentialEditorProps) {
  return (
    <Suspense
      fallback={
        <div
          className="h-[240px] rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground"
          role="status"
          aria-live="polite"
        >
          Loading editor…
        </div>
      }
    >
      <PotentialEditorInner {...props} />
    </Suspense>
  );
}
