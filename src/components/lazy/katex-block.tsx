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

export default function LazyBlockMath({ math }: { math: string }) {
  let html = "";
  try {
    html = katex.renderToString(math, {
      displayMode: true,
      throwOnError: false,
      trust: true,
      strict: "ignore",
    });
  } catch {
    // Belt-and-braces: even with throwOnError:false a pathological input
    // (or a missing katex runtime) must never blank the screen.
    return <code className="font-mono text-[11px] text-muted-foreground">{math}</code>;
  }
  return (
    <div
      data-testid="react-katex"
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
