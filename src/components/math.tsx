import { Suspense, lazy } from "react";

const LazyBlockMath = lazy(() => import("@/components/lazy/katex-block"));
const LazyInlineMath = lazy(() => import("@/components/lazy/katex-inline"));

/**
 * Thin facade over KaTeX that lazy-loads the renderer chunk on first
 * render. While the chunk streams in we show the raw LaTeX source — it's
 * still readable and avoids layout shift in formula panels.
 */
export function Math({ tex, block = false }: { tex: string; block?: boolean }) {
  const fallback = (
    <code className="font-mono text-[11px] text-muted-foreground">{tex}</code>
  );
  return (
    <Suspense fallback={fallback}>
      {block ? <LazyBlockMath math={tex} /> : <LazyInlineMath math={tex} />}
    </Suspense>
  );
}
