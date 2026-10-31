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

  // ─── QCompass multi-domain flags (default false) ─────────────────
  /** Master gate. When false, the app is byte-identical to today. */
  qcompassMultiDomain: boolean;
  qcompassChemistry: boolean;
  qcompassCondmat: boolean;
  qcompassAmo: boolean;
  qcompassHep: boolean;
  qcompassNuclear: boolean;
  qcompassGravity: boolean;
  qcompassStatmech: boolean;
  /** Gates the auth-token UI strip + apiFetch header injection. */
  qcompassAuth: boolean;
  /** Gates the /metrics tile + trace links on Research pages. */
  qcompassObservability: boolean;
  /**
   * Stream frames live (WebSocket transport, msgpack frames) on the
   * `/domains/$domain/visualizer/$id` route. When `false`, the route
   * renders the full-timeline JSON only. Independent of `liveBackend`
   * so we can stage the backend-API path in production while WS rolls
   * out behind a flag.
   */
  liveDomainStream: boolean;
}

/**
 * Backend base URL. When set, services call the compute API through the
 * generated SDK (`src/lib/sdk.ts`, P4-02); when unset, they read bundled
 * fixtures so local dev without a FastAPI process works.
 *
 * Per environment (P4-02/P3-07): local dev and the fixture e2e builds leave it
 * unset; staging and production builds get their Cloud Run API URL from the
 * deploy workflow, with the flags in `deploy/web/<environment>.env`.
 */
export const API_BASE_URL: string =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) || "";

const HAS_BACKEND = Boolean(API_BASE_URL);

/**
 * Where services read data. Exactly one source per build: `"api"` (the
 * compute API, never a fixture, never a fixture fallback after an API error)
 * or `"fixtures"` (bundled demo data, never the network API).
 */
export type DataSource = "api" | "fixtures";
export const DATA_SOURCE: DataSource = HAS_BACKEND ? "api" : "fixtures";

const envFlag = (key: string): boolean => {
  if (typeof import.meta === "undefined") return false;
  const v = import.meta.env?.[key as keyof ImportMetaEnv];
  return v === "true" || v === "1";
};

export const FEATURES: FeatureFlags = {
  liveBackend: HAS_BACKEND,
  liveAssistantToolDispatch: HAS_BACKEND,
  liveModelManagement: HAS_BACKEND,
  liveVisualization: HAS_BACKEND,
  persistRuns: true,
  auditToolCalls: true,
  domainsRegistry:
    typeof import.meta !== "undefined" && import.meta.env?.VITE_DOMAINS_REGISTRY === "false"
      ? false
      : true,

  qcompassMultiDomain: envFlag("VITE_QCOMPASS_MULTIDOMAIN"),
  qcompassChemistry: envFlag("VITE_QCOMPASS_CHEMISTRY"),
  qcompassCondmat: envFlag("VITE_QCOMPASS_CONDMAT"),
  qcompassAmo: envFlag("VITE_QCOMPASS_AMO"),
  qcompassHep: envFlag("VITE_QCOMPASS_HEP"),
  qcompassNuclear: envFlag("VITE_QCOMPASS_NUCLEAR"),
  qcompassGravity: envFlag("VITE_QCOMPASS_GRAVITY"),
  qcompassStatmech: envFlag("VITE_QCOMPASS_STATMECH"),
  qcompassAuth: envFlag("VITE_QCOMPASS_AUTH"),
  qcompassObservability: envFlag("VITE_QCOMPASS_OBSERVABILITY"),
  liveDomainStream:
    typeof import.meta !== "undefined" && import.meta.env?.VITE_LIVE_DOMAIN_STREAM === "true"
      ? true
      : false,
};
