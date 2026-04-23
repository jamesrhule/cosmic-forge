import "katex/dist/katex.min.css";
import { BlockMath, InlineMath } from "react-katex";

export function Math({ tex, block = false }: { tex: string; block?: boolean }) {
  return block ? <BlockMath math={tex} /> : <InlineMath math={tex} />;
}
