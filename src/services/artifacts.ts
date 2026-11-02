import { usesApi } from "@/lib/sdk";
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

/** The compute API has no artefact routes yet (artefacts live in run-artifacts storage). */
export const ARTIFACTS_UNAVAILABLE =
  "Run artefacts are not available from the API until P4-04/P4-06 (run-artifacts listing and download).";

/**
 * List downloadable artifacts for a completed (or failed) run.
 *
 * With `VITE_API_URL` this reports `NOT_IMPLEMENTED` instead of calling a
 * route that does not exist; otherwise it returns the bundled demo catalogue.
 */
export async function listArtifacts(runId: string): Promise<ArtifactRef[]> {
  if (usesApi()) {
    throw new ServiceError("NOT_IMPLEMENTED", ARTIFACTS_UNAVAILABLE);
  }
  return ARTIFACTS_BY_RUN[runId] ?? [];
}

/**
 * Download a single artifact as a Blob. Fixture mode reads from
 * /public/fixtures/artifacts/{ref.path}; with `VITE_API_URL` it reports
 * `NOT_IMPLEMENTED` until the API serves artefacts (P4-04/P4-06).
 */
export async function downloadArtifact(ref: ArtifactRef): Promise<Blob> {
  if (usesApi()) {
    throw new ServiceError("NOT_IMPLEMENTED", ARTIFACTS_UNAVAILABLE);
  }
  const url = `/fixtures/artifacts/${ref.path}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new ServiceError("NOT_FOUND", `Artifact not found: ${ref.path} (status ${res.status})`);
  }
  return res.blob();
}
