// Dynamically-imported chunk: the heavy KaTeX bundle (CSS + renderer).
// Importing this file is what triggers Rollup to emit a `katex.<hash>.js`
// chunk. Consumers should use `React.lazy(() => import(...))` to load it.
//
// We render KaTeX directly via `katex.renderToString` rather than using
// `react-katex` — that package ships a UMD bundle and a JSX source
// entry that both break under Vite's SSR module runner (named-export
// interop fails, and the source build crashes inside `prop-types`).
// Calling KaTeX ourselves is ~15 lines, has no peer-deps, and renders
// identically in SSR + client.
import "katex/dist/katex.min.css";
import katex from "katex";

// One-warn-per-source so a malformed LaTeX literal that re-renders
// every frame doesn't spam the console / telemetry.
import { trackWarn } from "@/lib/telemetry";
const warned = new Set<string>();
function warnOnce(src: string, reason: string) {
  if (warned.has(src)) return;
  warned.add(src);
  trackWarn("katex_render", reason, { src: src.slice(0, 120), display: "block" });
}

export default function LazyBlockMath({ math }: { math: string }) {
  let html = "";
  try {
    html = katex.renderToString(math, {
      displayMode: true,
      throwOnError: false,
      trust: true,
      strict: "ignore",
    });
  } catch (err) {
    // Belt-and-braces: even with throwOnError:false a pathological input
    // (or a missing katex runtime) must never blank the screen.
    warnOnce(math, `renderToString threw: ${(err as Error)?.message ?? err}`);
    return (
      <code
        data-katex-fallback="true"
        title="Failed to render LaTeX"
        className="font-mono text-[11px] text-muted-foreground"
      >
        {math}
      </code>
    );
  }
  // KaTeX with throwOnError:false embeds a `class="katex-error"` span on
  // bad input. Treat that as a fallback case too: the raw source is more
  // useful than KaTeX's red parser-error blob inside a panel.
  if (html.includes('class="katex-error"')) {
    warnOnce(math, "KaTeX produced katex-error span");
    return (
      <code
        data-katex-fallback="true"
        title="Failed to render LaTeX"
        className="font-mono text-[11px] text-muted-foreground"
      >
        {math}
      </code>
    );
  }
  return (
    <div
      data-testid="react-katex"
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
