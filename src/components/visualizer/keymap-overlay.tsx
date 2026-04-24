import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

/**
 * Press `?` anywhere in the visualizer to open. Lists every keyboard
 * shortcut. Closes on `?` again, Escape, or click-outside (Radix Dialog).
 *
 * Lives outside the panel grid so it overlays everything when open.
 * Listens globally but ignores `?` typed inside form fields.
 */

interface Shortcut {
  keys: string[];
  description: string;
  group: "Transport" | "Comparison" | "Frame export" | "General";
}

const SHORTCUTS: Shortcut[] = [
  { keys: ["Space"], description: "Play / pause", group: "Transport" },
  { keys: ["←"], description: "Step back one frame", group: "Transport" },
  { keys: ["→"], description: "Step forward one frame", group: "Transport" },
  { keys: ["Shift", "←"], description: "Jump back 10 frames", group: "Transport" },
  { keys: ["Shift", "→"], description: "Jump forward 10 frames", group: "Transport" },
  { keys: ["Home"], description: "Seek to first frame", group: "Transport" },
  { keys: ["End"], description: "Seek to last frame", group: "Transport" },
  { keys: ["1"], description: "0.25× speed", group: "Transport" },
  { keys: ["2"], description: "0.5× speed", group: "Transport" },
  { keys: ["3"], description: "1× speed", group: "Transport" },
  { keys: ["4"], description: "2× speed", group: "Transport" },
  { keys: ["5"], description: "5× speed", group: "Transport" },
  { keys: ["L"], description: "Toggle loop", group: "Transport" },
  { keys: ["O"], description: "Toggle A↔B overlay", group: "Comparison" },
  { keys: ["S"], description: "Toggle split screen", group: "Comparison" },
  { keys: ["P"], description: "Toggle sync-by-phase", group: "Comparison" },
  { keys: ["E"], description: "Export current frame as PNG", group: "Frame export" },
  { keys: ["?"], description: "Open this overlay", group: "General" },
  { keys: ["Esc"], description: "Close overlays", group: "General" },
];

const GROUPS: Shortcut["group"][] = ["Transport", "Comparison", "Frame export", "General"];

export function KeymapOverlay() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "?" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-base">Visualizer keyboard shortcuts</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          {GROUPS.map((g) => {
            const list = SHORTCUTS.filter((s) => s.group === g);
            if (list.length === 0) return null;
            return (
              <section key={g}>
                <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {g}
                </h4>
                <ul className="space-y-1.5">
                  {list.map((s) => (
                    <li
                      key={s.description}
                      className="flex items-center justify-between gap-3 text-xs"
                    >
                      <span className="text-foreground">{s.description}</span>
                      <span className="flex shrink-0 gap-1">
                        {s.keys.map((k) => (
                          <Kbd key={k}>{k}</Kbd>
                        ))}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
        <p className="pt-2 text-[11px] text-muted-foreground">
          Press <Kbd>?</Kbd> to toggle this overlay anywhere in the visualizer.
        </p>
      </DialogContent>
    </Dialog>
  );
}

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd
      className={cn(
        "inline-flex min-w-[1.5rem] items-center justify-center rounded border border-border bg-muted px-1.5 py-0.5",
        "font-mono text-[10px] leading-none text-foreground shadow-sm",
      )}
    >
      {children}
    </kbd>
  );
}
