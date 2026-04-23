import "katex/dist/katex.min.css";
import katexPkg from "react-katex";

const { BlockMath, InlineMath } = katexPkg as unknown as {
  BlockMath: React.ComponentType<{ math: string }>;
  InlineMath: React.ComponentType<{ math: string }>;
};

export function Math({ tex, block = false }: { tex: string; block?: boolean }) {
  return block ? <BlockMath math={tex} /> : <InlineMath math={tex} />;
}
