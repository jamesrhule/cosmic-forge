// Dynamically-imported chunk twin of katex-block, for inline math.
import "katex/dist/katex.min.css";
import { InlineMath } from "react-katex";

export default function LazyInlineMath({ math }: { math: string }) {
  return <InlineMath math={math} />;
}
