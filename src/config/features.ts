/**
 * Feature flags for the UCGLE-F1 Workbench shell.
 *
 * Today every flag below is `false`. The frontend reads them via the
 * service layer to decide whether to dispatch a real network call or
 * return a fixture. Claude Code will flip these (or wire them to env
 * vars) when the FastAPI backend, LLM router, and model manager are
 * connected.
 */
export interface FeatureFlags {
  liveBackend: boolean;
  liveAssistantToolDispatch: boolean;
  liveModelManagement: boolean;
  liveVisualization: boolean;
  /**
   * Persist run metadata + results + timelines into Lovable Cloud
   * (Postgres + Storage). When false, services keep returning fixtures
   * and `src/lib/persistence.ts` helpers no-op. Flip on once auth and
   * the run-creation UI are wired.
   */
  persistRuns: boolean;
  /**
   * Write a row to `tool_call_audit` for every assistant tool dispatch.
   * Independent of `liveAssistantToolDispatch` so we can audit fixture
   * runs locally before turning real dispatch on.
   */
  auditToolCalls: boolean;
}

export const FEATURES: FeatureFlags = {
  liveBackend: false,
  liveAssistantToolDispatch: false,
  liveModelManagement: false,
  liveVisualization: false,
  persistRuns: false,
  auditToolCalls: true,
};

/**
 * Backend base URL. Read but unused while liveBackend is false.
 * Claude Code will route fetch() calls here once flipped on.
 */
export const API_BASE_URL: string =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) || "";
