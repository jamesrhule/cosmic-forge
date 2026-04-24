import { MessageSquare } from "lucide-react";
import { useChat } from "@/store/ui";
import { cn } from "@/lib/utils";

/**
 * Floating bottom-right affordance to open the global ChatDrawer.
 *
 * Renders on every route via the root layout. Hides itself while the
 * drawer is open so it doesn't sit on top of the sheet's right edge.
 * The unread/context-chip badge surfaces pinned context counts so the
 * user notices when something was attached from the visualizer or
 * configurator.
 */
export function ChatTrigger() {
  const open = useChat((s) => s.open);
  const setOpen = useChat((s) => s.setOpen);
  const contextCount = useChat((s) => s.contextChips.length);

  if (open) return null;

  return (
    <button
      type="button"
      onClick={() => setOpen(true)}
      aria-label="Open assistant"
      className={cn(
        "fixed bottom-4 right-4 z-40 flex h-12 w-12 items-center justify-center rounded-full",
        "bg-primary text-primary-foreground shadow-lg ring-1 ring-black/5 transition-all",
        "hover:bg-primary/90 hover:shadow-xl active:scale-95",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
      )}
    >
      <MessageSquare className="h-5 w-5" aria-hidden="true" />
      {contextCount > 0 && (
        <span
          aria-label={`${contextCount} pinned context items`}
          className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full border-2 border-background bg-destructive px-1 font-mono text-[10px] font-semibold text-destructive-foreground"
        >
          {contextCount > 9 ? "9+" : contextCount}
        </span>
      )}
    </button>
  );
}
