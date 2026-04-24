import { Link } from "@tanstack/react-router";
import { MessageSquare } from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { Button } from "@/components/ui/button";
import { useChat } from "@/store/ui";
import { cn } from "@/lib/utils";

export interface ErrorPageProps {
  /** Big top-line title (e.g. "404", "Something went wrong"). */
  eyebrow?: string;
  title: string;
  description?: React.ReactNode;
  /** Primary CTA. Renders next to the secondary actions. */
  primaryAction?: React.ReactNode;
  /** Optional debug/error details surfaced in DEV only. */
  errorMessage?: string;
  /** Hide the "Open assistant" secondary action when no chat available. */
  hideAssistantAction?: boolean;
  className?: string;
}

/**
 * Shared shell for 404, route-error, and root-error surfaces. Wraps a
 * brand mark, primary/secondary actions, and an "Open assistant"
 * affordance so users always have a non-dead-end recovery path that
 * matches the rest of the chrome.
 */
export function ErrorPage({
  eyebrow,
  title,
  description,
  primaryAction,
  errorMessage,
  hideAssistantAction = false,
  className,
}: ErrorPageProps) {
  const openChat = useChat((s) => s.setOpen);

  return (
    <div
      className={cn(
        "flex min-h-screen flex-col items-center justify-center bg-background px-6 py-12 text-foreground",
        className,
      )}
    >
      <div className="w-full max-w-md text-center">
        <BrandMark size={56} className="mx-auto mb-6 text-primary" />
        {eyebrow && (
          <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            {eyebrow}
          </p>
        )}
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">{title}</h1>
        {description && (
          <div className="mt-3 text-sm text-muted-foreground">{description}</div>
        )}
        {import.meta.env.DEV && errorMessage && (
          <pre className="mt-5 max-h-40 overflow-auto rounded-md border bg-muted p-3 text-left font-mono text-xs text-destructive">
            {errorMessage}
          </pre>
        )}
        <div className="mt-7 flex flex-wrap items-center justify-center gap-2">
          {primaryAction ?? (
            <Button asChild>
              <Link to="/">Go home</Link>
            </Button>
          )}
          <Button asChild variant="outline">
            <Link to="/visualizer">Open Visualizer</Link>
          </Button>
          {!hideAssistantAction && (
            <Button
              variant="ghost"
              onClick={() => openChat(true)}
              className="gap-1.5"
            >
              <MessageSquare className="h-4 w-4" aria-hidden="true" />
              Open assistant
            </Button>
          )}
        </div>
        <p className="mt-8 font-mono text-[10px] text-muted-foreground">
          UCGLE-F1 Workbench
        </p>
      </div>
    </div>
  );
}
