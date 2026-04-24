import { FEATURES } from "@/config/features";
import { apiFetch, isBackendConfigured } from "@/lib/apiClient";
import { trackError } from "@/lib/telemetry";
import { ServiceError, type ArtifactRef } from "@/types/domain";

const ARTIFACTS_BY_RUN: Record<string, ArtifactRef[]> = {
  "kawai-kim-natural": [
    {
      runId: "kawai-kim-natural",
      name: "sgwb_spectrum.csv",
      path: "kawai-kim/sgwb_spectrum.csv",
      mimeType: "text/csv",
      sizeBytes: 12_480,
      description: "Stochastic GW background, 128 log-spaced frequency bins.",
    },
    {
      runId: "kawai-kim-natural",
      name: "audit_report.json",
      path: "kawai-kim/audit_report.json",
      mimeType: "application/json",
      sizeBytes: 7_212,
      description: "Full S1–S15 audit report with references.",
    },
    {
      runId: "kawai-kim-natural",
      name: "config.yaml",
      path: "kawai-kim/config.yaml",
      mimeType: "text/yaml",
      sizeBytes: 942,
      description: "Hydra-compatible run configuration.",
    },
  ],
  "starobinsky-standard": [
    {
      runId: "starobinsky-standard",
      name: "sgwb_spectrum.csv",
      path: "starobinsky/sgwb_spectrum.csv",
      mimeType: "text/csv",
      sizeBytes: 11_904,
      description: "Stochastic GW background, 128 log-spaced frequency bins.",
    },
    {
      runId: "starobinsky-standard",
      name: "config.yaml",
      path: "starobinsky/config.yaml",
      mimeType: "text/yaml",
      sizeBytes: 882,
      description: "Hydra-compatible run configuration.",
    },
  ],
  "gb-off-control": [
    {
      runId: "gb-off-control",
      name: "config.yaml",
      path: "gb-off/config.yaml",
      mimeType: "text/yaml",
      sizeBytes: 870,
      description: "Hydra-compatible run configuration (GB term disabled).",
    },
  ],
  "failing-run": [],
};

/**
 * List downloadable artifacts for a completed (or failed) run.
 *
 * Backend: GET /api/runs/{runId}/artifacts
 */
export async function listArtifacts(runId: string): Promise<ArtifactRef[]> {
  if (FEATURES.liveBackend && isBackendConfigured()) {
    try {
      return await apiFetch<ArtifactRef[]>(
        `/api/runs/${encodeURIComponent(runId)}/artifacts`,
      );
    } catch (err) {
      trackError("service_error", {
        scope: "list_artifacts_live_failed",
        runId,
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }
  return ARTIFACTS_BY_RUN[runId] ?? [];
}

/**
 * Download a single artifact as a Blob. Live backend serves a presigned
 * URL or streams bytes directly; fixture mode reads from
 * /public/fixtures/artifacts/{ref.path}.
 *
 * Backend: GET /api/runs/{runId}/artifacts/{name}
 */
export async function downloadArtifact(ref: ArtifactRef): Promise<Blob> {
  if (FEATURES.liveBackend && isBackendConfigured()) {
    try {
      // apiFetch returns text on non-JSON responses; we want the raw blob,
      // so fall through to a direct fetch with the auth header.
      const url = `/api/runs/${encodeURIComponent(ref.runId)}/artifacts/${encodeURIComponent(ref.name)}`;
      const blob = await downloadBlob(url);
      if (blob) return blob;
    } catch (err) {
      trackError("service_error", {
        scope: "download_artifact_live_failed",
        runId: ref.runId,
        name: ref.name,
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }
  const url = `/fixtures/artifacts/${ref.path}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new ServiceError("NOT_FOUND", `Artifact not found: ${ref.path} (status ${res.status})`);
  }
  return res.blob();
}

async function downloadBlob(path: string): Promise<Blob | null> {
  // Local helper so we don't pollute apiClient with blob-specific glue.
  const { API_BASE_URL } = await import("@/config/features");
  const { supabase } = await import("@/integrations/supabase/client");
  const base = API_BASE_URL.replace(/\/+$/, "");
  const { data: sess } = await supabase.auth.getSession();
  const token = sess.session?.access_token;
  const res = await fetch(`${base}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return null;
  return res.blob();
}
