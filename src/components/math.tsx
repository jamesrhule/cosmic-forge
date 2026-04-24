import { Suspense, lazy } from "react";
import { MathErrorBoundary } from "@/components/lazy/math-error-boundary";

const LazyBlockMath = lazy(() => import("@/components/lazy/katex-block"));
const LazyInlineMath = lazy(() => import("@/components/lazy/katex-inline"));

/**
 * Thin facade over KaTeX that lazy-loads the renderer chunk on first
 * render. While the chunk streams in we show the raw LaTeX source — it's
 * still readable and avoids layout shift in formula panels.
 *
 * The `<MathErrorBoundary>` is the safety net for the "vendor-katex
 * chunk failed to load" case — without it, a chunk-load failure would
 * leave the user on the Suspense fallback forever and bubble an
 * unhandled rejection up to the root error boundary.
 */
export function Math({ tex, block = false }: { tex: string; block?: boolean }) {
  const fallback = block ? (
    <code className="font-mono text-[11px] text-muted-foreground">{tex}</code>
  ) : (
    <span className="font-mono text-[11px] text-muted-foreground">{tex}</span>
  );
  return (
    <MathErrorBoundary tex={tex} inline={!block}>
      <Suspense fallback={fallback}>
        {block ? <LazyBlockMath math={tex} /> : <LazyInlineMath math={tex} />}
      </Suspense>
    </MathErrorBoundary>
  );
}
