import { apiFetch } from "@/lib/apiClient";
import { api, usesApi } from "@/lib/sdk";
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
 * With `VITE_API_URL` this asks the compute API (errors propagate; the API
 * has no artefact-listing route yet, so it answers 404 until one lands);
 * otherwise it returns the bundled demo catalogue.
 *
 * Backend: GET /api/runs/{runId}/artifacts
 */
export async function listArtifacts(runId: string): Promise<ArtifactRef[]> {
  if (usesApi()) {
    return apiFetch<ArtifactRef[]>(`/api/runs/${encodeURIComponent(runId)}/artifacts`);
  }
  return ARTIFACTS_BY_RUN[runId] ?? [];
}

/**
 * Download a single artifact as a Blob. With `VITE_API_URL` the compute API
 * serves the bytes; fixture mode reads from /public/fixtures/artifacts/{ref.path}.
 *
 * Backend: GET /api/runs/{runId}/artifacts/{name}
 */
export async function downloadArtifact(ref: ArtifactRef): Promise<Blob> {
  if (usesApi()) {
    const path = `/api/runs/${encodeURIComponent(ref.runId)}/artifacts/${encodeURIComponent(ref.name)}`;
    return api((c) => c.getBlob(path));
  }
  const url = `/fixtures/artifacts/${ref.path}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new ServiceError("NOT_FOUND", `Artifact not found: ${ref.path} (status ${res.status})`);
  }
  return res.blob();
}
