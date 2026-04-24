import { useState } from "react";
import { ChevronDown, X } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";

export interface RunPickerProps {
  /** Master (A-side) run id; excluded from the candidate list. */
  currentRunId: string;
  /** Currently-selected partner run id, or null. */
  partnerRunId: string | null;
  /** All run ids that ship a baked visualization (incl. currentRunId). */
  availableRunIds: string[];
  /** Called with the new partner id, or `null` to clear. */
  onChange: (runB: string | null) => void;
  className?: string;
}

/**
 * Compact partner-run picker for the visualizer header.
 *
 * Pure presentational: no router or store imports. The owning route is
 * responsible for translating `onChange` into a search-param navigation.
 */
export function RunPicker({
  currentRunId,
  partnerRunId,
  availableRunIds,
  onChange,
  className,
}: RunPickerProps) {
  const [open, setOpen] = useState(false);

  const candidates = availableRunIds.filter((id) => id !== currentRunId);
  const noCandidates = candidates.length === 0;

  const triggerLabel = partnerRunId ?? "Compare with…";

  return (
    <div className={cn("flex items-center gap-1", className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            disabled={noCandidates}
            title={
              noCandidates
                ? "Only one visualization fixture is available"
                : "Choose a partner run for A↔B comparison"
            }
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md border bg-background px-2 py-1 font-mono text-[11px] text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
              partnerRunId && "border-primary/40 text-foreground",
            )}
            aria-label={
              partnerRunId
                ? `Partner run: ${partnerRunId}. Change or clear.`
                : "Pick a partner run for comparison"
            }
          >
            {!partnerRunId ? (
              <span className="text-muted-foreground">Compare with…</span>
            ) : (
              <span className="max-w-[14rem] truncate">{triggerLabel}</span>
            )}
            <ChevronDown className="h-3 w-3 opacity-60" />
          </button>
        </PopoverTrigger>
        <PopoverContent
          align="start"
          sideOffset={6}
          className="w-72 p-0"
        >
          <Command>
            <CommandInput placeholder="Search runs…" className="h-9" />
            <CommandList>
              <CommandEmpty>No matching runs.</CommandEmpty>
              <CommandGroup heading="Partner run">
                {candidates.map((id) => (
                  <CommandItem
                    key={id}
                    value={id}
                    onSelect={() => {
                      onChange(id);
                      setOpen(false);
                    }}
                    className="font-mono text-xs"
                  >
                    <span
                      className={cn(
                        "mr-2 inline-block h-1.5 w-1.5 rounded-full",
                        id === partnerRunId
                          ? "bg-primary"
                          : "bg-transparent",
                      )}
                    />
                    {id}
                  </CommandItem>
                ))}
              </CommandGroup>
              <CommandSeparator />
              <CommandGroup>
                <CommandItem
                  value="__clear__"
                  disabled={!partnerRunId}
                  onSelect={() => {
                    onChange(null);
                    setOpen(false);
                  }}
                  className="text-xs text-muted-foreground data-[disabled=true]:opacity-40"
                >
                  Clear partner
                </CommandItem>
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {partnerRunId ? (
        <button
          type="button"
          onClick={() => onChange(null)}
          aria-label="Clear partner run"
          title="Clear partner run"
          className="inline-flex h-[22px] w-[22px] items-center justify-center rounded-md border bg-background text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <X className="h-3 w-3" />
        </button>
      ) : null}
    </div>
  );
}
