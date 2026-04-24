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
  /**
   * QCompass Phase 1: exposes the multi-domain plugin shell (domain
   * selector chip in the header, registry endpoints). When false the
   * UI is visually identical to the UCGLE-F1-only build. The cosmology
   * code path runs unchanged either way.
   */
  domainsRegistry: boolean;
}

/**
 * Backend base URL. When set, services route through `apiFetch` /
 * `apiSse` (see `src/lib/apiClient.ts`); when unset, services fall back
 * to bundled fixtures so local dev without a FastAPI process works.
 */
export const API_BASE_URL: string =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) || "";

const HAS_BACKEND = Boolean(API_BASE_URL);

export const FEATURES: FeatureFlags = {
  liveBackend: HAS_BACKEND,
  liveAssistantToolDispatch: HAS_BACKEND,
  liveModelManagement: HAS_BACKEND,
  liveVisualization: HAS_BACKEND,
  persistRuns: true,
  auditToolCalls: true,
  domainsRegistry:
    typeof import.meta !== "undefined" &&
    import.meta.env?.VITE_DOMAINS_REGISTRY === "false"
      ? false
      : true,
};
