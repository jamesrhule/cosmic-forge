// Dynamically-imported chunk twin of katex-block, for inline math.
// See katex-block.tsx for the rationale on bypassing `react-katex`.
import "katex/dist/katex.min.css";
import katex from "katex";

export default function LazyInlineMath({ math }: { math: string }) {
  let html = "";
  try {
    html = katex.renderToString(math, {
      displayMode: false,
      throwOnError: false,
      trust: true,
      strict: "ignore",
    });
  } catch {
    return <code className="font-mono text-[11px] text-muted-foreground">{math}</code>;
  }
  return (
    <span
      data-testid="react-katex"
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
