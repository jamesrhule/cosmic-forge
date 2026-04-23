import type { ModelDescriptor } from "@/types/domain";
import { formatBytes } from "@/lib/utils";
import { Cpu, Cloud } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ModelBadgeProps {
  descriptor: ModelDescriptor;
  className?: string;
}

export function ModelBadge({ descriptor, className }: ModelBadgeProps) {
  const Icon = descriptor.provider === "local" ? Cpu : Cloud;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded border bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground",
        className,
      )}
      title={`${descriptor.displayName} · ${descriptor.format} · ${
        descriptor.sizeBytes ? formatBytes(descriptor.sizeBytes) : "remote"
      }`}
    >
      <Icon className="h-3 w-3" />
      {descriptor.displayName}
    </span>
  );
}
