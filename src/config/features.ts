/**
 * Feature flags for the UCGLE-F1 Workbench shell.
 *
 * Today every flag below is `false`. The frontend reads them via the
 * service layer to decide whether to dispatch a real network call or
 * return a fixture. Claude Code will flip these (or wire them to env
 * vars) when the FastAPI backend, LLM router, and model manager are
 * connected.
 */
export const FEATURES = {
  /** Enable real HTTP/SSE/WebSocket calls instead of fixture data. */
  liveBackend: false,
  /** Allow assistant to dispatch tool calls back into the app. */
  liveAssistantToolDispatch: false,
  /** Enable real model installation flows (filesystem writes). */
  liveModelManagement: false,
  /** Enable real visualization render/stream calls instead of fixtures. */
  liveVisualization: false,
} as const;

/**
 * Backend base URL. Read but unused while liveBackend is false.
 * Claude Code will route fetch() calls here once flipped on.
 */
export const API_BASE_URL: string =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) || "";
