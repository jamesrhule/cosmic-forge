import { ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ArxivLinkProps {
  id: string;
  className?: string;
  showIcon?: boolean;
}

export function ArxivLink({ id, className, showIcon = true }: ArxivLinkProps) {
  return (
    <a
      href={`https://arxiv.org/abs/${id}`}
      target="_blank"
      rel="noreferrer noopener"
      className={cn(
        "inline-flex items-center gap-1 rounded border bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground hover:bg-accent hover:text-accent-foreground",
        className,
      )}
    >
      arXiv:{id}
      {showIcon && <ExternalLink className="h-3 w-3" />}
    </a>
  );
}
