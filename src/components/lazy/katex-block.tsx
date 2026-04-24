// Dynamically-imported chunk: the heavy KaTeX bundle (CSS + react-katex).
// Importing this file is what triggers Rollup to emit a `katex.<hash>.js`
// chunk. Consumers should use `React.lazy(() => import(...))` to load it.
import "katex/dist/katex.min.css";
import pkg from "react-katex";

const { BlockMath } = pkg as unknown as { BlockMath: React.ComponentType<{ math: string }> };

export default function LazyBlockMath({ math }: { math: string }) {
  return <BlockMath math={math} />;
}
