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
  /**
   * QCompass multi-domain shell.
   *
   * When false (default), the workbench behaves exactly as the
   * UCGLE-F1 cosmology shell. When true, the top-nav reveals a
   * `DomainSwitcher` and the chemistry routes under
   * `/domains/chemistry/*` become reachable. The cosmology views
   * are byte-identical at the default flag setting; flipping the
   * flag MUST never change cosmology behaviour, only reveal the
   * chemistry tabs.
   */
  qcompassMultiDomain: false,
} as const;

/**
 * Backend base URL. Read but unused while liveBackend is false.
 * Claude Code will route fetch() calls here once flipped on.
 */
export const API_BASE_URL: string =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) || "";
