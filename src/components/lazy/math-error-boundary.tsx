import { Component, type ReactNode } from "react";
import { trackError } from "@/lib/telemetry";

interface Props {
  /** Raw LaTeX source — shown verbatim if rendering / chunk-load fails. */
  tex: string;
  /** Render `<span>` instead of `<code>` for inline math. */
  inline?: boolean;
  children: ReactNode;
}

interface State {
  failed: boolean;
}

/**
 * Catches errors raised while rendering the lazy KaTeX chunks (the most
 * common cause being a chunk-load failure after a deploy: the dynamic
 * import promise rejects with "Failed to fetch dynamically imported
 * module" and React's `<Suspense>` re-throws it past us).
 *
 * Rendering the raw LaTeX here is strictly better than the default
 * Suspense behaviour of leaving the user on a stale fallback forever.
 */
export class MathErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    // Surface chunk-load failures into the same telemetry channel as the
    // global listener in `installChunkErrorListener` so dashboards can
    // pivot on a single event name.
    trackError("chunk_load_error", { source: "math-error-boundary", message: msg });
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.warn("[MathErrorBoundary] caught:", msg);
    }
  }

  render() {
    if (this.state.failed) {
      const Tag = this.props.inline ? "span" : "code";
      return (
        <Tag
          data-katex-fallback="true"
          title="Failed to render LaTeX"
          className="font-mono text-[11px] text-muted-foreground"
        >
          {this.props.tex}
        </Tag>
      );
    }
    return this.props.children;
  }
}
