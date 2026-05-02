/**
 * QCompass — Model-domain badge (nuclear / gravity surrogate marker).
 *
 * @example
 *   <ModelDomainBadge value="1+1D_toy" />
 */
import { Badge } from "@/components/ui/badge";

export interface ModelDomainBadgeProps {
  value: string | null | undefined;
}

const TONE: Record<string, string> = {
  "1+1D_toy": "border-amber-500/50 bg-amber-500/10 text-amber-600 dark:text-amber-400",
  few_body_3d: "border-emerald-500/50 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  effective_hamiltonian: "border-sky-500/50 bg-sky-500/10 text-sky-600 dark:text-sky-400",
  learned_surrogate: "border-red-500/50 bg-red-500/10 text-red-600 dark:text-red-400",
};

export function ModelDomainBadge({ value }: ModelDomainBadgeProps) {
  if (!value) return null;
  const klass = TONE[value] ?? "border-muted bg-muted text-muted-foreground";
  return (
    <Badge variant="outline" className={`font-mono text-[11px] ${klass}`}>
      model_domain · {value}
    </Badge>
  );
}
