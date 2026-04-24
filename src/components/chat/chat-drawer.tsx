import { useEffect, useRef, useState } from "react";
import { MessageSquare, X, Send, Loader2, Trash2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { useChat } from "@/store/ui";
import { sendMessage } from "@/services/assistant";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/domain";

/**
 * Stable id generator. Prefers `crypto.randomUUID` (available in modern
 * browsers and Node ≥ 19, including the Worker SSR runtime). Falls back
 * to `crypto.getRandomValues` for older Safari, and only as a last
 * resort uses `Math.random` — which is acceptable here because chat
 * message ids are non-security-sensitive client identifiers.
 */
const newId = (): string => {
  if (typeof crypto !== "undefined") {
    if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
    if (typeof crypto.getRandomValues === "function") {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
    }
  }
  return `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
};

/**
 * Minimal assistant drawer.
 *
 * Reads the global `useChat` store so any surface can pin context (the
 * Configurator's "Ask assistant", the visualizer panels' "Pin frame to
 * assistant" context-menu, etc.) and the same drawer renders. Streams
 * fixture responses today; swap `sendMessage` for the live SSE/WebSocket
 * call once `FEATURES.liveBackend` flips.
 */
export function ChatDrawer() {
  const open = useChat((s) => s.open);
  const setOpen = useChat((s) => s.setOpen);
  const messages = useChat((s) => s.messages);
  const draft = useChat((s) => s.draft);
  const setDraft = useChat((s) => s.setDraft);
  const appendMessage = useChat((s) => s.appendMessage);
  const patchLastAssistant = useChat((s) => s.patchLastAssistant);
  const isStreaming = useChat((s) => s.isStreaming);
  const setStreaming = useChat((s) => s.setStreaming);
  const conversationId = useChat((s) => s.conversationId);
  const selectedModelId = useChat((s) => s.selectedModelId);
  const contextChips = useChat((s) => s.contextChips);
  const removeContext = useChat((s) => s.removeContext);
  const clearContext = useChat((s) => s.clearContext);
  const newConversation = useChat((s) => s.newConversation);

  const scrollRef = useRef<HTMLDivElement>(null);
  const [submitting, setSubmitting] = useState(false);

  // Auto-scroll to bottom on new content.
  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isStreaming]);

  const handleSend = async () => {
    const text = draft.trim();
    if (!text || submitting) return;
    setSubmitting(true);
    setStreaming(true);

    const userMsg: ChatMessage = {
      id: newId(),
      role: "user",
      content: text,
      createdAt: new Date().toISOString(),
    };
    const assistantMsg: ChatMessage = {
      id: newId(),
      role: "assistant",
      content: "",
      createdAt: new Date().toISOString(),
      modelId: selectedModelId,
    };
    appendMessage(userMsg);
    appendMessage(assistantMsg);
    setDraft("");

    try {
      const stream = sendMessage({
        conversationId,
        messages: [...messages, userMsg],
        modelId: selectedModelId,
      });
      for await (const evt of stream) {
        if (evt.type === "token") {
          patchLastAssistant(evt.delta);
        } else if (evt.type === "error") {
          toast.error("Assistant error", { description: evt.message });
          break;
        }
      }
    } catch (err) {
      toast.error("Assistant failed", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setSubmitting(false);
      setStreaming(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent
        side="right"
        className="flex w-full flex-col gap-0 p-0 sm:max-w-[460px]"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-primary" />
            <span className="text-sm font-semibold">Assistant</span>
            <Badge variant="outline" className="font-mono text-[10px]">
              {selectedModelId}
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 px-2 text-[11px]"
              onClick={() => {
                if (
                  messages.length > 0 &&
                  !confirm("Clear this conversation? This can't be undone.")
                ) {
                  return;
                }
                newConversation();
                clearContext();
              }}
              disabled={messages.length === 0 && contextChips.length === 0}
              aria-label="Clear conversation"
              title="Clear conversation"
            >
              <Trash2 className="h-3 w-3" aria-hidden="true" />
              Clear
            </Button>
          </div>
        </div>

        {/* Context chip strip */}
        {contextChips.length > 0 && (
          <div className="flex flex-wrap gap-1.5 border-b bg-muted/30 px-4 py-2">
            {contextChips.map((chip, i) => (
              <span
                key={`${chip.kind}-${i}`}
                className="inline-flex items-center gap-1 rounded-full border bg-background px-2 py-0.5 font-mono text-[10px] text-muted-foreground"
              >
                <span className="font-medium text-foreground">
                  {chip.kind}
                </span>
                <span className="max-w-[180px] truncate">{chip.label}</span>
                <button
                  type="button"
                  onClick={() => removeContext(i)}
                  aria-label="Remove context chip"
                  className="rounded-sm hover:bg-muted"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3">
          {messages.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="space-y-4">
              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} streaming={isStreaming} />
              ))}
            </div>
          )}
        </div>

        {/* Composer */}
        <div className="border-t bg-background p-3">
          <div className="flex items-end gap-2">
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about a run, request a comparison, suggest parameters…"
              rows={2}
              className="min-h-[44px] resize-none text-sm"
              disabled={submitting}
            />
            <Button
              type="button"
              size="icon"
              onClick={() => void handleSend()}
              disabled={submitting || draft.trim().length === 0}
              aria-label="Send message"
            >
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="mt-1.5 text-[10px] text-muted-foreground">
            Enter to send · Shift+Enter for newline · Fixture mode (no live
            backend)
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center text-xs text-muted-foreground">
      <MessageSquare className="mb-3 h-8 w-8 opacity-30" />
      <p>No conversation yet.</p>
      <p className="mt-1 max-w-[280px]">
        Try “Compare these runs”, “Summarise the audit”, or “Suggest
        parameters for a stronger SGWB peak.”
      </p>
    </div>
  );
}

function MessageBubble({
  message,
  streaming,
}: {
  message: ChatMessage;
  streaming: boolean;
}) {
  const isUser = message.role === "user";
  const isEmpty = message.content.length === 0;
  return (
    <div className={cn("flex flex-col", isUser ? "items-end" : "items-start")}>
      <div
        className={cn(
          "max-w-[90%] rounded-md px-3 py-2 text-sm",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground",
        )}
      >
        {isEmpty && streaming ? (
          <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            thinking…
          </span>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none [&>p]:my-1 [&>pre]:my-2">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
      <span className="mt-0.5 px-1 font-mono text-[10px] text-muted-foreground">
        {message.role}
        {message.modelId ? ` · ${message.modelId}` : ""}
      </span>
    </div>
  );
}
