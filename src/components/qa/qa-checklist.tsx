import { useEffect, useMemo, useState } from "react";
import { QA_CHECKLIST, flatRowIds } from "@/lib/qa-checklist-data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "ucgle.qa.checklist.v1";

function loadState(): Record<string, boolean> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (parsed && typeof parsed === "object") return parsed as Record<string, boolean>;
  } catch {
    /* ignore corrupt state */
  }
  return {};
}

function saveState(state: Record<string, boolean>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* private mode */
  }
}

export function QaChecklist() {
  const [state, setState] = useState<Record<string, boolean>>({});
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setState(loadState());
    setHydrated(true);
  }, []);

  const toggle = (id: string) => {
    setState((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      saveState(next);
      return next;
    });
  };

  const reset = () => {
    setState({});
    saveState({});
  };

  const { done, total } = useMemo(() => {
    const ids = flatRowIds();
    const d = ids.filter((id) => state[id]).length;
    return { done: d, total: ids.length };
  }, [state]);

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-6 py-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight">Resize checklist</h2>
          <p className="text-xs text-muted-foreground">
            Mirrors <code className="font-mono text-[11px]">docs/qa/chart-resizing.md</code>. Ticks
            persist to localStorage.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
            {hydrated ? `${done} / ${total}` : `… / ${total}`}
          </span>
          <Button variant="ghost" size="sm" onClick={reset} disabled={!hydrated}>
            Reset
          </Button>
        </div>
      </div>

      {QA_CHECKLIST.map((section) => (
        <Card key={section.title}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{section.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {section.intro && <p className="text-xs text-muted-foreground">{section.intro}</p>}
            <ul className="divide-y rounded-md border bg-card">
              {section.rows.map((row) => {
                const checked = !!state[row.id];
                return (
                  <li key={row.id}>
                    <label
                      className={cn(
                        "flex cursor-pointer items-start gap-3 px-3 py-2 text-sm hover:bg-muted/50",
                        checked && "text-muted-foreground line-through",
                      )}
                    >
                      <input
                        type="checkbox"
                        className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer accent-[color:var(--color-accent-indigo)]"
                        checked={checked}
                        onChange={() => toggle(row.id)}
                      />
                      <div className="space-y-0.5">
                        <div>{row.step}</div>
                        <div className="text-xs text-muted-foreground">→ {row.expected}</div>
                      </div>
                    </label>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
