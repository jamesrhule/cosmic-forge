// Dynamically-imported chunk twin of katex-block, for inline math.
import "katex/dist/katex.min.css";
import pkg from "react-katex";

const { InlineMath } = pkg as unknown as { InlineMath: React.ComponentType<{ math: string }> };

export default function LazyInlineMath({ math }: { math: string }) {
  return <InlineMath math={math} />;
}
