/**
 * QCompass — Domain selector chip.
 *
 * Header chip listing all registered + Phase 2 placeholder domains.
 * Only `cosmology.ucglef1` is enabled in Phase 1; the others render as
 * disabled rows with their `disabledReason` tooltip.
 *
 * Mounted only when `FEATURES.domainsRegistry === true`; with the flag
 * off, this component is never rendered and the UI is identical to
 * the UCGLE-F1-only build.
 */

import { useMemo } from "react";
import { Compass, Lock } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { listDomainSurface } from "@/lib/domains/registry";
// Side-effect import: registers cosmology.ucglef1 with the registry.
import "@/lib/domains/cosmology.ucglef1";

export function DomainSelector() {
  const surface = useMemo(() => listDomainSurface(), []);
  const active = surface.find((d) => d.enabled) ?? surface[0];

  return (
    <TooltipProvider delayDuration={200}>
      <DropdownMenu>
        <DropdownMenuTrigger
          className="inline-flex items-center gap-1.5 rounded-md border bg-muted px-2 py-1 font-mono text-[11px] text-muted-foreground hover:bg-muted/70"
          aria-label="Select physics domain"
        >
          <Compass className="size-3" />
          <span>{active?.label ?? "Domain"}</span>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-72">
          <DropdownMenuLabel className="text-xs text-muted-foreground">
            QCompass · Physics domain
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {surface.map((d) => (
            <DomainRow key={d.id} entry={d} />
          ))}
          <DropdownMenuSeparator />
          <div className="px-2 py-1.5 text-[10px] text-muted-foreground">
            Phase 1 ships cosmology only. Other domains land per the QCompass
            roadmap (chemistry first).
          </div>
        </DropdownMenuContent>
      </DropdownMenu>
    </TooltipProvider>
  );
}

function DomainRow({
  entry,
}: {
  entry: ReturnType<typeof listDomainSurface>[number];
}) {
  const row = (
    <DropdownMenuItem
      disabled={!entry.enabled}
      className="flex flex-col items-start gap-0.5"
    >
      <div className="flex w-full items-center gap-2">
        <span className="text-sm font-medium">{entry.label}</span>
        {!entry.enabled && <Lock className="ml-auto size-3 text-muted-foreground" />}
      </div>
      <span className="text-[11px] text-muted-foreground">{entry.description}</span>
    </DropdownMenuItem>
  );
  if (entry.enabled) return row;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div>{row}</div>
      </TooltipTrigger>
      <TooltipContent side="left" className="text-xs">
        {entry.disabledReason ?? "Not yet available"}
      </TooltipContent>
    </Tooltip>
  );
}
