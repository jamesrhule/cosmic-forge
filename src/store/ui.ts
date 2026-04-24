import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatMessage, ModelDescriptor, RunConfig, RunResult } from "@/types/domain";

/* ─────────────────────────── Theme ─────────────────────────── */

type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggle: () => void;
}

export const useTheme = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "light",
      setTheme: (theme) => {
        set({ theme });
        applyTheme(theme);
      },
      toggle: () => {
        const next: Theme = get().theme === "light" ? "dark" : "light";
        set({ theme: next });
        applyTheme(next);
      },
    }),
    { name: "ucgle-theme" },
  ),
);

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
}

/* ─────────────────────────── Chat drawer ─────────────────────────── */

export type AssistantContextChip =
  | { kind: "config"; label: string; config: RunConfig }
  | { kind: "run"; label: string; runId: string }
  | { kind: "runs"; label: string; runIds: string[] }
  | { kind: "benchmark"; label: string; benchmarkId: string }
  | { kind: "selection"; label: string; selection: string }
  | {
      kind: "visualizer_frame";
      label: string;
      runId: string;
      frameIndex: number;
      tau: number;
    }
  | {
      kind: "visualizer_comparison";
      label: string;
      runIdA: string;
      runIdB: string;
      frameIndex: number;
    };

interface ChatState {
  open: boolean;
  width: number;
  unread: number;
  contextChips: AssistantContextChip[];
  conversationId: string;
  messages: ChatMessage[];
  selectedModelId: string;
  draft: string;
  isStreaming: boolean;
  /* model manager */
  modelManagerOpen: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
  setWidth: (w: number) => void;
  addContext: (chip: AssistantContextChip) => void;
  removeContext: (index: number) => void;
  clearContext: () => void;
  newConversation: () => void;
  appendMessage: (m: ChatMessage) => void;
  patchLastAssistant: (delta: string) => void;
  setSelectedModel: (id: string) => void;
  setDraft: (s: string) => void;
  setStreaming: (b: boolean) => void;
  bumpUnread: () => void;
  clearUnread: () => void;
  openModelManager: () => void;
  closeModelManager: () => void;
}

const newId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

export const useChat = create<ChatState>()((set, get) => ({
  open: false,
  width: 450,
  unread: 0,
  contextChips: [],
  conversationId: newId(),
  messages: [],
  selectedModelId: "llama-3.1-8b-instruct-q4",
  draft: "",
  isStreaming: false,
  modelManagerOpen: false,

  setOpen: (open) => {
    set({ open });
    if (open) set({ unread: 0 });
  },
  toggle: () => {
    const open = !get().open;
    set({ open, unread: open ? 0 : get().unread });
  },
  setWidth: (w) => set({ width: Math.min(720, Math.max(360, w)) }),
  addContext: (chip) =>
    set((s) => ({
      contextChips: [...s.contextChips.filter((c) => c.kind !== chip.kind), chip],
    })),
  removeContext: (index) =>
    set((s) => ({ contextChips: s.contextChips.filter((_, i) => i !== index) })),
  clearContext: () => set({ contextChips: [] }),
  newConversation: () =>
    set({
      conversationId: newId(),
      messages: [],
      draft: "",
      isStreaming: false,
    }),
  appendMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  patchLastAssistant: (delta) =>
    set((s) => {
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "assistant") {
          msgs[i] = { ...msgs[i], content: msgs[i].content + delta };
          break;
        }
      }
      return { messages: msgs };
    }),
  setSelectedModel: (id) => set({ selectedModelId: id }),
  setDraft: (s) => set({ draft: s }),
  setStreaming: (b) => set({ isStreaming: b }),
  bumpUnread: () => set((s) => ({ unread: s.open ? 0 : s.unread + 1 })),
  clearUnread: () => set({ unread: 0 }),
  openModelManager: () => set({ modelManagerOpen: true }),
  closeModelManager: () => set({ modelManagerOpen: false }),
}));

/* ─────────────────────────── Run selection (Control view) ─────────────────────────── */

interface RunSelectionState {
  selectedIds: string[];
  toggle: (id: string) => void;
  set: (ids: string[]) => void;
  clear: () => void;
}

export const useRunSelection = create<RunSelectionState>()((set, get) => ({
  selectedIds: [],
  toggle: (id) => {
    const cur = get().selectedIds;
    set({
      selectedIds: cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id],
    });
  },
  set: (ids) => set({ selectedIds: ids }),
  clear: () => set({ selectedIds: [] }),
}));

/* ─────────────────────────── Loaded runs counter (footer) ─────────────────────────── */

interface MetaState {
  loadedRunCount: number;
  setLoadedRunCount: (n: number) => void;
  buildSha: string;
  installedDefaultModel: ModelDescriptor | null;
  setInstalledDefault: (m: ModelDescriptor | null) => void;
}

export const useMeta = create<MetaState>()((set) => ({
  loadedRunCount: 0,
  setLoadedRunCount: (n) => set({ loadedRunCount: n }),
  buildSha: "static-shell-2025.04",
  installedDefaultModel: null,
  setInstalledDefault: (m) => set({ installedDefaultModel: m }),
}));

/* ─────────────────────────── Command palette ─────────────────────────── */

interface CommandPaletteState {
  open: boolean;
  setOpen: (b: boolean) => void;
  toggle: () => void;
}

export const useCommandPalette = create<CommandPaletteState>()((set, get) => ({
  open: false,
  setOpen: (open) => set({ open }),
  toggle: () => set({ open: !get().open }),
}));
