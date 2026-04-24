// Dynamically-imported chunk twin of katex-block, for inline math.
// See katex-block.tsx for the rationale on bypassing `react-katex`.
import "katex/dist/katex.min.css";
import katex from "katex";

const warned = new Set<string>();
function warnOnce(src: string, reason: string) {
  if (warned.has(src)) return;
  warned.add(src);
  // eslint-disable-next-line no-console
  console.warn(`[katex] ${reason}:`, src.slice(0, 120));
}

export default function LazyInlineMath({ math }: { math: string }) {
  let html = "";
  try {
    html = katex.renderToString(math, {
      displayMode: false,
      throwOnError: false,
      trust: true,
      strict: "ignore",
    });
  } catch (err) {
    warnOnce(math, `renderToString threw: ${(err as Error)?.message ?? err}`);
    return (
      <span
        data-katex-fallback="true"
        title="Failed to render LaTeX"
        className="font-mono text-[11px] text-muted-foreground"
      >
        {math}
      </span>
    );
  }
  if (html.includes('class="katex-error"')) {
    warnOnce(math, "KaTeX produced katex-error span");
    return (
      <span
        data-katex-fallback="true"
        title="Failed to render LaTeX"
        className="font-mono text-[11px] text-muted-foreground"
      >
        {math}
      </span>
    );
  }
  return (
    <span
      data-testid="react-katex"
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
