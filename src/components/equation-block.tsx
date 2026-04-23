import "katex/dist/katex.min.css";
import { Copy, Check } from "lucide-react";
import { useState } from "react";
import { BlockMath } from "react-katex";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface EquationBlockProps {
  latex: string;
  copyable?: boolean;
  className?: string;
}

export function EquationBlock({
  latex,
  copyable = false,
  className,
}: EquationBlockProps) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(latex);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard not available — silent */
    }
  };

  return (
    <div
      className={cn(
        "group relative rounded-md border bg-card px-4 py-3 text-card-foreground",
        className,
      )}
    >
      <div className="overflow-x-auto">
        <BlockMath math={latex} />
      </div>
      {copyable && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onCopy}
          className="absolute right-2 top-2 h-7 px-2 opacity-0 transition group-hover:opacity-100"
          aria-label="Copy LaTeX"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        </Button>
      )}
    </div>
  );
}
