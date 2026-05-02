/**
 * QCompass — "Coming online" card.
 *
 * Minimum-viable result/visualizer renderer used by every non-
 * carve-out domain in the scaffolding pass. NOT a literal stub:
 * it consumes real fixture data so the full data path is exercised.
 *
 * @example
 *   <ComingOnlineCard
 *     title="Chemistry result"
 *     fields={[{ label: "Energy", value: -1.137, units: "Ha" }]}
 *   />
 */
import { Card } from "@/components/ui/card";
import { Sci } from "@/components/sci";

export interface ComingOnlineField {
  label: string;
  value: number | string | null | undefined;
  units?: string;
}

export interface ComingOnlineCardProps {
  title: string;
  description?: string;
  fields: ComingOnlineField[];
  footer?: string;
}

export function ComingOnlineCard({
  title,
  description,
  fields,
  footer = "Rich rendering coming online in a follow-up pass.",
}: ComingOnlineCardProps) {
  return (
    <Card className="space-y-3 p-4">
      <header>
        <h3 className="font-medium">{title}</h3>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </header>
      <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {fields.map((f) => (
          <div key={f.label} className="flex flex-col gap-0.5">
            <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">
              {f.label}
            </dt>
            <dd className="font-mono text-sm">
              {typeof f.value === "number" ? <Sci value={f.value} /> : (f.value ?? "—")}
              {f.units ? <span className="ml-1 text-xs text-muted-foreground">{f.units}</span> : null}
            </dd>
          </div>
        ))}
      </dl>
      <p className="border-t pt-2 text-[11px] italic text-muted-foreground">{footer}</p>
    </Card>
  );
}
